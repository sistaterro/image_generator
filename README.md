# Image Generator

Image generator that starts a local ComfyUI server and runs workflows through a single Python client.

## Requirements

- Windows
- Python 3.11
- GPU/configuration compatible with ComfyUI
- Required models downloaded manually

## Installation

From the project root:

```bat
py -3.11 -m venv env
call env\Scripts\activate.bat
pip install -r requirements.txt
```

Then prepare the ComfyUI environment:

```bat
cd comfy_server\ComfyUI
py -3.11 -m venv env
call env\Scripts\activate.bat
pip install -r requirements.txt
```

If you are using an NVIDIA GPU, install the PyTorch build with the CUDA version that matches your machine before running ComfyUI.

## Models

Models are not versioned. Place them under:

```text
comfy_server/ComfyUI/models/
```

### Checkpoints

Place these in `comfy_server/ComfyUI/models/checkpoints/`:

- [`juggernautXL_ragnarokBy.safetensors`](https://civitai.com/models/133005/juggernaut-xl)
- [`cyberrealistic_final.safetensors`](https://civitai.com/models/15003/cyberrealistic)
- [`realvisxlV50_v50LightningBakedvae.safetensors`](https://civitai.com/models/139562/realvisxl-v50)

### LoRAs

Place this in `comfy_server/ComfyUI/models/loras/`:

- [`p400_sdxl.safetensors`](https://civitai.com/models/2192396/p400-color-film-or-sdxl-lora)

### VAE

Place this in `comfy_server/ComfyUI/models/vae/`:

- [`ae.safetensors`](https://huggingface.co/ffxvs/vae-flux/blob/main/ae.safetensors)

### GGUF

Place these where your GGUF custom nodes expect them. In this setup, that is usually:

- [`comfy_server/ComfyUI/models/unet/flux1-schnell-Q4_K_S.GGUF`](https://huggingface.co/city96/FLUX.1-schnell-gguf/blob/main/flux1-schnell-Q4_K_S.gguf)
- [`comfy_server/ComfyUI/models/clip/t5-v1_1-xxl-encoder-Q4_K_M.gguf`](https://huggingface.co/city96/t5-v1_1-xxl-encoder-gguf/blob/main/t5-v1_1-xxl-encoder-Q4_K_M.gguf)

If ComfyUI cannot find a GGUF file, open ComfyUI, inspect the matching loader node, and move the file to the folder shown by that node.

## Custom Nodes

Custom nodes are not versioned either. Some workflows may require external nodes installed in:

```text
comfy_server/ComfyUI/custom_nodes/
```

Install them with ComfyUI Manager or manually, following the error ComfyUI shows when loading each workflow.

## First-Use Checklist

This project includes an interactive setup checklist that helps a lot during first use:

```text
docs/checklist.html
```

The easiest way to open it is from the project root:

```bat
docs\open_checklist.bat
```

You can also double-click `docs\open_checklist.bat` in File Explorer. The batch file lives next to `checklist.html` and opens the page in your default browser.

Checklist progress is saved automatically in your browser with localStorage, so closing and reopening the page does not lose the checked items.

## Usage

Run the default flow:

```bat
run.bat
```

Or run it manually:

```bat
call env\Scripts\activate.bat
python main.py
```

The default mode uses `workflows/negative_fixed_2.json`, reads prompts from `prompts/*.txt`, and saves results in `output/`.

## Tags

List available workflows:

```bat
python main.py --list-tags
```

Run a specific workflow:

```bat
python main.py --tag flux
python main.py --tag realvis
python main.py --tag cyberrealistic
python main.py --tag cozy
```

You can also use the tag as the first argument:

```bat
python main.py flux
python main.py realvis "portrait photo, studio lighting"
python main.py "direct prompt with the default workflow"
```

## Runs

Each tag defines its run count in `main.py`, inside `WORKFLOWS`.

You can also override it from the command line:

```bat
python main.py --runs 1
python main.py --tag flux --runs 5
```

## Automatic Shutdown

To run the generator and schedule Windows shutdown 20 minutes after completion:

```bat
shutdown_run.bat
```

Internally, it runs:

```bat
python main.py --shutdown
```
