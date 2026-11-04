---
name: upscalex
description: Production-grade 8K and 16K image upscaler CLI and Model Context Protocol (MCP) server powered by RealESRGAN, Vulkan GPU hardware acceleration, and Lanczos supersampling. Use when upscaling images, converting low-resolution assets to 8K/16K, inspecting image DPI for print viability, or preparing assets for digital print and posters.
---

# UpscaleX Agent Skill

This skill equips AI agents (Claude, Cursor, Antigravity, Windsurf, Codex) with the knowledge and execution patterns required to inspect, validate, and upscale images to 8K and 16K resolutions using UpscaleX.

---

## When to Activate

Trigger this skill whenever the user:
- Requests to upscale, enlarge, or enhance an image resolution (e.g., "upscale this image to 16k", "make an 8k version", "sharpen this low-res photo").
- Mentions RealESRGAN, super-resolution, gigapixel prints, or high-DPI poster preparation.
- Asks whether an image has sufficient resolution for physical printing at 300 DPI (e.g., A1, A2, 24x36 inch poster).
- Needs to eliminate compression noise, pixelation, or blurry artifacts from 2D illustrations, photos, or digital art.

---

## Execution Modes

Agents can interact with UpscaleX via two channels:
1. **MCP Tools** (when the MCP server is registered in the client environment).
2. **CLI Executable** (using the terminal command `upscalex`).

---

## 1. MCP Tools Reference

When connected via Model Context Protocol, the following tools are available:

### `upscale_image`
Upscales an image file to high-resolution targets.

**Parameters:**
- `image_path` (string, required): Absolute path to the source image file.
- `target` (string, optional, default `"16k"`): Target resolution preset. Options: `"16k"`, `"8k"`, `"4k"`, `"4x"`, `"2x"`, or explicit `"WIDTHxHEIGHT"`.
- `model` (string, optional, default `"realesrgan-x4plus"`):
  - `"realesrgan-x4plus"`: Photorealistic images, real-world scenes, nature, textures, prints.
  - `"realesrgan-x4plus-anime"`: 2D digital art, anime, comics, vector-like graphics.
- `output_path` (string, optional): Destination file path. If omitted, saves next to source image.
- `tile_size` (integer, optional, default `256`): GPU tile size. Use `256` for GPUs with 4GB-6GB VRAM.
- `gpu_id` (integer, optional, default `1`): Vulkan device index (`1` for discrete NVIDIA/AMD GPU).
- `tta` (boolean, optional, default `false`): Enable Test-Time Augmentation (higher quality, 8x longer runtime).

### `get_image_metadata`
Inspects image dimensions, color space, file size, and calculated print dimensions at 300 DPI.

**Parameters:**
- `image_path` (string, required): Absolute path to the image file.

### `calculate_print_dpi`
Calculates the physical print fidelity (DPI) for a target print width and height.

**Parameters:**
- `image_path` (string, required): Absolute path to the image.
- `print_width_inches` (number, required): Intended print width (e.g. `24.0`).
- `print_height_inches` (number, required): Intended print height (e.g. `36.0`).

### `list_available_models`
Lists all available neural network weights and specifications.

---

## 2. CLI Execution Reference

If MCP tools are not directly exposed, execute commands through the shell:

```bash
# 1. Inspect image properties and 300 DPI print measurements
upscalex info "/path/to/image.png"

# 2. Upscale to 16K (native 4x RealESRGAN)
upscalex upscale "/path/to/image.png" --target 16k

# 3. Upscale to 8K (supersampled with Lanczos anti-aliasing)
upscalex upscale "/path/to/image.png" --target 8k -o "/path/to/image_8k.png"

# 4. Upscale Anime or Vector Art
upscalex upscale "/path/to/art.png" --model realesrgan-x4plus-anime --target 8k

# 5. Custom Print Dimensions
upscalex upscale "/path/to/banner.png" --target 12000x8000 --tile-size 400
```

---

## Best Practices and Rules for Agents

1. **Resolution Presets**:
   - For ultra-high-resolution print masters, recommend `--target 16k` (4× native upscale).
   - For web displays or crisp poster files, recommend `--target 8k` (4× upscale downscaled via Lanczos-3 for supersampled anti-aliasing with zero noise).
2. **VRAM Safety**:
   - Always retain `--tile-size 256` on 4GB-6GB GPUs (such as RTX 3050 Laptop).
   - Only increase `--tile-size` to `400` or `600` on dedicated desktop cards with 8GB-16GB+ VRAM.
3. **Decompression Bomb Guard**:
   - When processing resulting 8K/16K images in downstream Python scripts, always set `Image.MAX_IMAGE_PIXELS = None` before calling `Image.open()`. Multi-hundred-megapixel files exceed Pillow's default 178M pixel threshold.
4. **Model Selection**:
   - Photos, real estate, landscapes, posters: `realesrgan-x4plus`.
   - Cartoons, logos, line art, anime: `realesrgan-x4plus-anime`.
