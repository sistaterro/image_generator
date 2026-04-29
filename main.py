import argparse
import copy
import json
import os
import random
import sys
import urllib.parse
import urllib.request
import uuid

import websocket


COMFY_URL = "127.0.0.1:8188"
PROMPTS_DIR = "prompts"
OUTPUT_DIR = "output"

DEFAULT_NEGATIVE_PROMPT = (
    "worst quality, low quality, lowres, bad anatomy, deformed body, mutation, "
    "disfigured, watermark, signature, text, bad hands, extra fingers, missing "
    "fingers, fused fingers, too many fingers, extra limbs, extra arms, merged "
    "hands, overlapping hands, extra hands, three hands, deformed hands, mutated "
    "hands, bad fingers, tangled fingers, impossible hand position, cloned face, "
    "deformed face, bad face, asymmetrical eyes, crossed eyes, black eyes, empty "
    "eyes, dead eyes, glassy eyes, distorted eyes, extra eyes, floating head, "
    "disembodied head, extra pens, two pens, duplicate objects, cartoon, "
    "animation, 3d render, clay, toy, pixar, illustration, stylized, painting, "
    "plastic skin, smooth skin"
)

WORKFLOWS = {
    "default": {
        "path": "workflows/negative_fixed_2.json",
        "runs": 3,
        "positive": {"node": "4", "fields": {"text_g": "{prompt}", "text_l": ""}},
    },
    "flux": {
        "path": "workflows/Flux FINAL.json",
        "runs": 3,
        "positive": {"node": "4", "fields": {"text": "{prompt}"}},
    },
    "cyberrealistic": {
        "path": "workflows/cyberrealistic workflow.json",
        "runs": 1,
        "positive": {"node": "6", "fields": {"text": "{prompt}"}},
        "negative": {"node": "7", "fields": {"text": DEFAULT_NEGATIVE_PROMPT}},
    },
    "realvis": {
        "path": "workflows/realvis.json",
        "runs": 1,
        "positive": {"node": "6", "fields": {"text": "{prompt}"}},
        "negative": {"node": "7", "fields": {"text": DEFAULT_NEGATIVE_PROMPT}},
    },
    "cozy": {
        "path": "workflows/cozy.json",
        "runs": 1,
        "positive": {"node": "4", "fields": {"text_g": "{prompt}", "text_l": ""}},
    },
}

ALIASES = {
    "main": "default",
    "negative": "default",
    "sdxl": "default",
    "cyber": "cyberrealistic",
}


def normalize_tag(tag: str) -> str:
    clean_tag = tag.strip().lower().lstrip("#@")
    return ALIASES.get(clean_tag, clean_tag)


def read_prompt_files() -> list[tuple[str, list[str]]]:
    if not os.path.exists(PROMPTS_DIR):
        print(f"Prompt folder was not found: '{PROMPTS_DIR}'")
        return []

    files = sorted(f for f in os.listdir(PROMPTS_DIR) if f.endswith(".txt"))
    if not files:
        print(f"No .txt files found in '{PROMPTS_DIR}'")
        return []

    result = []
    for file_name in files:
        name = os.path.splitext(file_name)[0]
        path = os.path.join(PROMPTS_DIR, file_name)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        prompts = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
        print(f"{file_name} -> {len(prompts)} prompts")
        result.append((name, prompts))

    return result


def ui_workflow_to_api(workflow_ui: dict) -> dict:
    link_map = {}
    for link in workflow_ui.get("links", []):
        link_id, source_node, source_slot, _, _, _ = link
        link_map[link_id] = [str(source_node), source_slot]

    def extract_ksampler_widgets(values):
        return {
            "seed": random.randint(0, 2**32 - 1),
            "steps": values[2],
            "cfg": values[3],
            "sampler_name": values[4],
            "scheduler": values[5],
            "denoise": values[6],
        }

    api = {}
    for node in workflow_ui.get("nodes", []):
        nid = str(node["id"])
        class_type = node["type"]

        connected_inputs = {}
        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is not None:
                connected_inputs[inp["name"]] = link_map[link_id]

        wv = node.get("widgets_values", [])
        widget_inputs = {}

        if class_type == "KSampler":
            widget_inputs = extract_ksampler_widgets(wv)
        elif class_type == "CLIPTextEncodeSDXL":
            widget_inputs = {
                "width": wv[0],
                "height": wv[1],
                "crop_w": wv[2],
                "crop_h": wv[3],
                "target_width": wv[4],
                "target_height": wv[5],
                "text_g": wv[6],
                "text_l": wv[7] if len(wv) > 7 else "",
            }
        elif class_type == "CLIPTextEncode":
            widget_inputs = {"text": wv[0]}
        elif class_type == "CheckpointLoaderSimple":
            widget_inputs = {"ckpt_name": wv[0]}
        elif class_type == "LoraLoader":
            widget_inputs = {
                "lora_name": wv[0],
                "strength_model": wv[1],
                "strength_clip": wv[2],
            }
        elif class_type == "EmptyLatentImage":
            widget_inputs = {"width": wv[0], "height": wv[1], "batch_size": wv[2]}
        elif class_type == "ImageScale":
            widget_inputs = {
                "upscale_method": wv[0],
                "width": wv[1],
                "height": wv[2],
                "crop": wv[3],
            }
        elif class_type == "SaveImage":
            widget_inputs = {"filename_prefix": wv[0]}
        else:
            idx = 0
            for inp in node.get("inputs", []):
                if "widget" in inp and inp.get("link") is None and idx < len(wv):
                    widget_inputs[inp["name"]] = wv[idx]
                    idx += 1

        api[nid] = {"class_type": class_type, "inputs": {**connected_inputs, **widget_inputs}}

    return api


def apply_fields(api_workflow: dict, rule: dict, prompt: str) -> None:
    node_id = rule["node"]
    if node_id not in api_workflow:
        raise KeyError(f"Workflow does not contain node {node_id}")

    for field, value in rule["fields"].items():
        api_workflow[node_id]["inputs"][field] = value.replace("{prompt}", prompt)


def inject_prompt(api_workflow: dict, prompt: str, profile: dict) -> dict:
    apply_fields(api_workflow, profile["positive"], prompt)
    if "negative" in profile:
        apply_fields(api_workflow, profile["negative"], prompt)
    return api_workflow


def queue_prompt(api_workflow: dict) -> tuple[str, str]:
    client_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": api_workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{COMFY_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Error HTTP {e.code}: {e.read().decode()}")
        raise

    prompt_id = data["prompt_id"]
    print(f"Queued | ID: {prompt_id}")
    return prompt_id, client_id


def wait_and_get_images(prompt_id: str, client_id: str) -> list[dict]:
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFY_URL}/ws?clientId={client_id}")
    print("Generating...\n")

    try:
        while True:
            msg = ws.recv()
            if isinstance(msg, str):
                data = json.loads(msg)
                event_type = data.get("type", "")
                if event_type == "progress":
                    step = data["data"]["value"]
                    total = data["data"]["max"]
                    bar = "#" * int((step / total) * 20)
                    print(f"\r[{bar:<20}] {step}/{total}", end="", flush=True)
                elif event_type == "executing" and data["data"].get("node") is None:
                    print("\nDone")
                    break
    finally:
        ws.close()

    with urllib.request.urlopen(f"http://{COMFY_URL}/history/{prompt_id}") as resp:
        history = json.loads(resp.read())

    images = []
    for _, output in history.get(prompt_id, {}).get("outputs", {}).items():
        for img in output.get("images", []):
            if img.get("type") == "output":
                images.append(img)

    return images


def download_image(img_info: dict, folder: str) -> str:
    params = urllib.parse.urlencode(
        {
            "filename": img_info["filename"],
            "subfolder": img_info.get("subfolder", ""),
            "type": "output",
        }
    )
    destination = os.path.join(folder, img_info["filename"])
    os.makedirs(folder, exist_ok=True)

    with urllib.request.urlopen(f"http://{COMFY_URL}/view?{params}") as resp:
        with open(destination, "wb") as f:
            f.write(resp.read())

    print(f"Saved: {destination}")
    return destination


def load_workflow(profile: dict) -> dict:
    with open(profile["path"], "r", encoding="utf-8") as f:
        return json.load(f)


def generate(prompt: str, output_folder: str, profile: dict) -> list[str]:
    workflow_ui = load_workflow(profile)
    api_wf = ui_workflow_to_api(workflow_ui)
    api_wf = inject_prompt(api_wf, prompt, profile)
    pid, cid = queue_prompt(api_wf)
    images = wait_and_get_images(pid, cid)
    return [download_image(img, output_folder) for img in images]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single ComfyUI image generation client with workflow tags."
    )
    parser.add_argument("items", nargs="*", help="Direct prompt or tag + prompt.")
    parser.add_argument("--tag", "--workflow", dest="tag", default="default")
    parser.add_argument("--runs", type=int, help="Override the configured run count.")
    parser.add_argument("--list-tags", action="store_true")
    parser.add_argument("--shutdown", action="store_true", help="Shut down Windows after 20 minutes.")
    args = parser.parse_args(argv)

    if args.items:
        possible_tag = normalize_tag(args.items[0])
        if possible_tag in WORKFLOWS:
            args.tag = possible_tag
            args.items = args.items[1:]

    args.tag = normalize_tag(args.tag)
    if args.tag not in WORKFLOWS and not args.list_tags:
        tags = ", ".join(sorted(WORKFLOWS))
        parser.error(f"Unknown tag '{args.tag}'. Available tags: {tags}")

    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.list_tags:
        for tag, profile in sorted(WORKFLOWS.items()):
            print(f"{tag}: {profile['path']}")
        return 0

    profile = copy.deepcopy(WORKFLOWS[args.tag])
    if args.runs is not None:
        profile["runs"] = args.runs

    print(f"Workflow: {args.tag} -> {profile['path']}")

    if args.items:
        prompt = " ".join(args.items)
        print(f"\nPrompt: {prompt}")
        files = generate(prompt, OUTPUT_DIR, profile)
        for file_path in files:
            print(f"   -> {file_path}")
        print("\nFinished.")
        return 0

    collections = read_prompt_files()
    if not collections:
        print("Nothing to process.")
        return 1

    total_images = 0
    for run_idx in range(1, profile["runs"] + 1):
        print(f"\n{'=' * 60}")
        print(f"RUN {run_idx}/{profile['runs']}")
        print(f"{'=' * 60}")

        for name, prompts in collections:
            output_folder = os.path.join(OUTPUT_DIR, name)
            total = len(prompts)
            print(f"\n{'-' * 50}")
            print(f"{name} ({total} images -> output/{name}/)")
            print(f"{'-' * 50}")

            for i, prompt in enumerate(prompts, 1):
                print(f"\n[{i}/{total}] {prompt}")
                files = generate(prompt, output_folder, profile)
                for file_path in files:
                    print(f"   -> {file_path}")
                total_images += len(files)

    print(f"\nFinished. {total_images} image(s) generated.")

    if args.shutdown:
        os.system("shutdown -s -t 1200")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
