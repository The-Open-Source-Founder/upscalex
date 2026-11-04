# UpscaleX Command-Line Interface (CLI) Guide

This guide provides technical specifications, operational instructions, and configuration parameters for the `upscalex` command-line tool.

---

## Command Overview

The CLI provides five core subcommands:

| Subcommand | Function |
| :--- | :--- |
| `upscale` | Execute high-resolution image upscaling using RealESRGAN models. |
| `info` | Inspect pixel dimensions, megapixels, color space, and print sizes at 300 DPI. |
| `doctor` | Inspect cross-platform environment, detected GPUs, and CPU fallback capabilities. |
| `models` | List all available pre-trained neural network models and their specifications. |
| `download-engine` | Manually download and verify the precompiled Vulkan binary for your operating system. |
| `serve` | Run the Model Context Protocol (MCP) server over standard input/output. |

---

## 1. `upscale` Command Reference

### Syntax

```bash
upscalex upscale [OPTIONS] IMAGE_PATH
```

### Arguments

- `IMAGE_PATH` *(Required)*: Path to the input image file (supported formats: PNG, JPG, JPEG, WEBP, BMP).

### Options

| Flag | Long Option | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `-t` | `--target` | String | `16k` | Target resolution preset or explicit dimension (`16k`, `8k`, `4k`, `4x`, `2x`, or `WIDTHxHEIGHT`). |
| `-m` | `--model` | Choice | `realesrgan-x4plus` | Model identifier: `realesrgan-x4plus`, `realesrgan-x4plus-anime`, `realesr-animevideov3-x2`, `realesr-animevideov3-x3`, `realesr-animevideov3-x4`. |
| `-o` | `--output` | Path | None | Explicit path for the processed output file. If omitted, the file is saved adjacent to the input with a resolution suffix. |
| | `--tile-size` | Integer | `256` | GPU tile dimension in pixels. Essential for managing VRAM allocation and preventing Out-Of-Memory errors. |
| `-g` | `--gpu-id` | String | `auto` | Vulkan compute device index (`auto` auto-selects discrete GPU, integer ID `0`/`1`, or `cpu` for multi-threaded CPU fallback). |
| `-x` | `--tta` | Flag | `False` | Enables Test-Time Augmentation (8-pass rotational inference) for maximum visual fidelity at the cost of processing duration. |

### Usage Examples

#### 16K Master Upscale (Default)
```bash
upscalex upscale poster.png --target 16k
```
Upscales a 4K image (`4,024 × 6,252`) directly to 16K (`16,096 × 25,008`, ~402.5 MP) using the 4× RealESRGAN deep-learning model.

#### 8K Supersampled Upscale
```bash
upscalex upscale photo.jpg --target 8k -o photo_8k.png
```
Executes a 4× RealESRGAN upscale, then downscales the resulting master to 8K resolution using Lanczos-3 resampling. This method acts as Supersampling Anti-Aliasing (SSAA), removing high-frequency artifacts while retaining edge sharpness.

#### Anime / Vector Illustration Mode
```bash
upscalex upscale artwork.png --model realesrgan-x4plus-anime --target 8k
```
Uses the specialized anime weights optimized for flat color regions, bold line art, and zero ringing artifacts.

#### Custom Target Dimensions
```bash
upscalex upscale banner.png --target 12000x8000 --tile-size 400
```

---

## 2. VRAM and Tile Size Management

RealESRGAN processes images using a sliding-window spatial tile mechanism. Selecting the appropriate `--tile-size` ensures stable execution without exceeding physical GPU memory.

| VRAM Capacity | Recommended `--tile-size` | Notes |
| :--- | :--- | :--- |
| **4 GB VRAM** | `256` | Optimal for laptop GPUs (e.g. RTX 3050 Laptop). Eliminates memory allocation spikes. |
| **6 GB – 8 GB VRAM** | `400` | Standard setting for desktop mid-tier GPUs (RTX 3060, RTX 4060). |
| **12 GB – 16 GB VRAM** | `600` | Faster throughput with fewer tile overlap boundaries. |
| **24 GB+ VRAM** | `0` (Auto) | Engine automatically allocates maximum spatial tiles or full frame if within bounds. |

---

## 3. `info` Command Reference

Inspects an image and computes target print measurements at industry standard 300 DPI (dots per inch).

### Syntax

```bash
upscalex info IMAGE_PATH
```

### Sample Output

```
    Image Metadata: client_image.png     
+---------------------------------------+
| Field                | Value          |
|----------------------+----------------|
| Dimensions           | 4024 x 6252    |
| Megapixels           | 25.16 MP       |
| Aspect Ratio         | 0.6436 (W:H)   |
| Color Mode           | RGB            |
| Format               | PNG            |
| File Size            | 29.17 MB       |
| Print Size (300 DPI) | 13.4 x 20.8 in |
| Print Size (Metric)  | 34.1 x 52.9 cm |
+---------------------------------------+
```

---

## 4. `doctor` Command Reference

Inspects the host system environment, detects available Vulkan compute devices, and verifies CPU fallback capabilities across Windows, Linux, and macOS.

### Syntax

```bash
upscalex doctor
```

### Sample Output

```
                    UpscaleX System & Hardware Diagnostics                     
+-----------------------------------------------------------------------------+
| Component             | Details                                             |
|-----------------------+-----------------------------------------------------|
| Operating System      | Windows (11) / Linux (Ubuntu) / macOS (Darwin)      |
| Architecture          | AMD64 / ARM64 (Apple Silicon)                       |
| Python Version        | 3.10+                                               |
| CPU Logical Cores     | 12                                                  |
| Vulkan GPU Available  | Yes (or No in Headless/CI environments)              |
| GPU [0]               | Intel(R) UHD Graphics                               |
| GPU [1]               | NVIDIA GeForce RTX 3050 Laptop GPU (Discrete /      |
|                       | Default)                                            |
| Default Mode          | Vulkan GPU (Device 1: NVIDIA GeForce RTX 3050)      |
| Recommended Tile Size | 256px                                               |
+-----------------------------------------------------------------------------+
```

---

## 5. `models` Command Reference

Lists available neural network models, scale factors, and recommended applications.

```bash
upscalex models
```

### Model Matrix

- **`realesrgan-x4plus`** (Scale: 4×): General photorealistic imagery, fine-art reproductions, architectural renders, and natural textures.
- **`realesrgan-x4plus-anime`** (Scale: 4×): 2D illustrations, vector-like graphics, comic scans, and digital artwork with sharp edges.
- **`realesr-animevideov3-x2` / `x3` / `x4`**: Lightweight architecture designed for video frames and rapid turnaround assets.

---

## 5. `download-engine` Command Reference

Verifies the presence of the precompiled Vulkan engine and models. If missing, it downloads and unpacks the official platform binary into the application cache directory (`%LOCALAPPDATA%/realesrgan-upscaler` on Windows, `~/.cache/realesrgan-upscaler` on Linux).

```bash
upscalex download-engine
```
