# Agent Handoff Notes

## Project Goal

This repository is a local image-generation runner. It starts an embedded ComfyUI server from `comfy_server/ComfyUI`, then runs a single Python client, `main.py`, to submit prompts to ComfyUI workflows and download generated images into the project-level `output/` folder.

The project is intended to be portable as one working block: the app code, workflows, and ComfyUI server code live in the same repository, while large/runtime assets stay out of Git.

## High-Level Flow

1. `run.bat` starts ComfyUI from `comfy_server/ComfyUI`.
2. It waits for `http://<local-ip>:8188/system_stats` to respond.
3. It activates the project Python environment at `env/`.
4. It runs `python main.py`.
5. `main.py` reads prompts, converts a ComfyUI UI workflow JSON into API format, injects prompts, queues jobs, waits on the websocket, then downloads generated images into `output/`.

`shutdown_run.bat` follows the same flow, but runs `python main.py --shutdown`, which schedules Windows shutdown 20 minutes after completion.

## Repository Structure

```text
.
+-- AGENTS.md
+-- README.md
+-- main.py
+-- requirements.txt
+-- run.bat
+-- shutdown_run.bat
+-- prompts/
|   +-- prompt_image.txt
+-- workflows/
|   +-- Flux FINAL.json
|   +-- cozy.json
|   +-- cyberrealistic workflow.json
|   +-- negative_fixed_2.json
|   +-- realvis.json
+-- comfy_server/
    +-- ComfyUI/
```

## Main Entry Points

- `run.bat`: default user entry point.
- `shutdown_run.bat`: same generation flow plus delayed Windows shutdown.
- `main.py`: single Python client for all workflows.
- `docs/checklist.html`: interactive first-use checklist. Progress is stored in the browser with localStorage.

There used to be one Python script per workflow. That was intentionally consolidated into `main.py`.

## Workflow Tags

Workflow selection is configured in `main.py` inside the `WORKFLOWS` dictionary.

Current tags:

- `default`: `workflows/negative_fixed_2.json`, 3 runs
- `flux`: `workflows/Flux FINAL.json`, 3 runs
- `cyberrealistic`: `workflows/cyberrealistic workflow.json`, 1 run
- `realvis`: `workflows/realvis.json`, 1 run
- `cozy`: `workflows/cozy.json`, 1 run

Aliases:

- `main` -> `default`
- `negative` -> `default`
- `sdxl` -> `default`
- `cyber` -> `cyberrealistic`

Useful commands:

```bat
python main.py
python main.py --list-tags
python main.py --tag flux
python main.py flux
python main.py realvis "portrait photo, studio lighting"
python main.py --tag flux --runs 5
```

## Prompt Input

Default mode reads every `.txt` file in `prompts/`.

Each non-empty, non-comment line becomes one prompt. Lines starting with `#` are ignored.

The file `prompts/prompt_image.txt` is an example prompt file and should stay versioned.

## Output Behavior

Project-level generated images are saved under:

```text
output/
```

This folder is intentionally ignored by Git.

Do not automatically delete ComfyUI's internal output folder. The user may use the embedded ComfyUI separately from this runner, so `comfy_server/ComfyUI/output/` should be left alone unless the user explicitly asks otherwise.

## ComfyUI Server

The embedded ComfyUI code lives at:

```text
comfy_server/ComfyUI/
```

`run.bat` sets:

```bat
set "COMFY_DIR=%BASE_DIR%comfy_server\ComfyUI"
set "COMFY_PORT=8188"
```

ComfyUI is launched with:

```bat
python main.py --listen 0.0.0.0 --port 8188
```

The batch files expose ComfyUI on `0.0.0.0` and probe a local IPv4 address for readiness.

## Ignored Runtime Assets

The root `.gitignore` intentionally excludes:

- `env/`
- `output/`
- `.vscode/`
- `comfy_server/ComfyUI/env/`
- `comfy_server/ComfyUI/models/`
- `comfy_server/ComfyUI/output/`
- `comfy_server/ComfyUI/temp/`
- `comfy_server/ComfyUI/input/`
- `comfy_server/ComfyUI/user/`
- `comfy_server/ComfyUI/custom_nodes/`
- Python caches and bytecode

Do not commit generated images, Python virtual environments, downloaded models, or custom-node installations unless the user explicitly changes that policy.

## Required Models

Models are documented in `README.md` and are not versioned.

Expected locations:

```text
comfy_server/ComfyUI/models/checkpoints/
comfy_server/ComfyUI/models/loras/
comfy_server/ComfyUI/models/vae/
comfy_server/ComfyUI/models/unet/
comfy_server/ComfyUI/models/clip/
```

Required model files:

- `juggernautXL_ragnarokBy.safetensors`
- `cyberrealistic_final.safetensors`
- `realvisxlV50_v50LightningBakedvae.safetensors`
- `p400_sdxl.safetensors`
- `ae.safetensors`
- `flux1-schnell-Q4_K_S.GGUF`
- `t5-v1_1-xxl-encoder-Q4_K_M.gguf`

The Flux workflow needs `ae.safetensors`; it is loaded by a `VAELoader` node and is not included in the GGUF model file.

## Custom Nodes

`custom_nodes/` is ignored. Some workflows may require custom nodes installed locally. The README tells users to install them through ComfyUI Manager or manually based on ComfyUI load errors.

Do not assume custom nodes are versioned.

## Development Notes

- Keep user-facing CLI messages and docs in English.
- Keep `main.py` as the single workflow runner.
- Prefer adding workflow support by editing the `WORKFLOWS` dictionary rather than creating new Python scripts.
- Preserve default behavior: `python main.py` should behave like the original `comfy_client.py` did, using `negative_fixed_2.json`, reading `prompts/*.txt`, and running 3 passes.
- Be careful with ComfyUI paths: the project intentionally uses relative paths so it can move as a block.
- Do not delete or clean `comfy_server/ComfyUI/output/` automatically.
- Keep `prompts/prompt_image.txt` versioned as a first-use example.

## Git State

The repository remote is:

```text
https://github.com/sistaterro/image_generator.git
```

The primary branch is `main`.
