# UpscaleX MCP/CLI 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP: Enabled](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Vulkan GPU](https://img.shields.io/badge/Acceleration-Vulkan%20GPU-orange.svg)](https://www.khronos.org/vulkan/)

**UpscaleX MCP/CLI** is a production-grade **8K/16K image upscaler CLI** and **Model Context Protocol (MCP) server** powered by **RealESRGAN**, **Vulkan GPU hardware acceleration**, and **Lanczos supersampling**.

Designed for high-end digital print shops, poster production, gallery artwork, and autonomous AI agents in Claude Desktop, Antigravity, and Cursor.

---

## ✨ Features

- 🖥️ **Dual Interface**: Full-featured interactive CLI (`upscalex`) and standard Model Context Protocol server (`upscalex-mcp`).
- 🎯 **8K & 16K Ultra-Resolution Presets**:
  - **16K**: Native 4× RealESRGAN deep-learning model upscale (up to 400+ Megapixels).
  - **8K**: 4× deep-learning upscale downscaled via high-precision Lanczos resampling (SSAA supersampling antialiasing) for razor-sharp lines and zero noise.
  - **4K / Custom**: Scale to any custom resolution or print aspect ratio.
- ⚡ **Zero-CUDA Hassle**: Uses Vulkan C++ runtime—runs at full hardware speed on NVIDIA, AMD, and Intel GPUs without compiling CUDA wheels.
- 🧩 **Smart VRAM Tiling**: Configurable GPU tiling (`--tile-size 256`) processes ultra-gigapixel images without Out-Of-Memory (OOM) crashes on 4GB/6GB/8GB GPUs.
- 🛡️ **Decompression Bomb Protection Bypass**: Configured with automatic PIL safety overrides for multi-gigabyte print bitmaps.
- 📦 **Automated Engine Downloader**: Automatically retrieves and validates the official precompiled Real-ESRGAN binary if not already installed.
- 📐 **Print Sizing & DPI Inspector**: Calculates physical print dimensions (inches/cm) at 300 DPI (Gallery standard), 150 DPI, and 72 DPI.

---

## 🚀 Quickstart with `uv`

### 1. Installation

Clone the repository and install with [`uv`](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/your-username/upscalex.git
cd upscalex

# Create environment and install
uv venv
uv pip install -e .
```

### 2. Verify Available Models & Engine

```bash
upscalex models
```

---

## 💻 CLI Usage

### Upscale an Image to 16K (Default)
```bash
upscalex upscale input.png --target 16k
```

### Upscale an Image to 8K (Supersampled)
```bash
upscalex upscale poster.png --target 8k -o poster_8k.png
```

### Upscale Anime / Digital Illustrations
```bash
upscalex upscale artwork.png --model realesrgan-x4plus-anime --target 8k
```

### Inspect Image & Print Sizing at 300 DPI
```bash
upscalex info client_poster.png
```

### CLI Command Options

| Option | Flag | Default | Description |
| :--- | :--- | :--- | :--- |
| `--target` | `-t` | `16k` | Target resolution: `16k`, `8k`, `4k`, `4x`, `2x`, or `WIDTHxHEIGHT` |
| `--model` | `-m` | `realesrgan-x4plus` | Pre-trained model (`realesrgan-x4plus`, `realesrgan-x4plus-anime`) |
| `--output` | `-o` | Auto | Destination file path |
| `--tile-size` | | `256` | Tile size in pixels (safe for 4GB VRAM) |
| `--gpu-id` | `-g` | `1` | Vulkan GPU index (typically `1` for discrete NVIDIA laptop GPU) |
| `--tta` | `-x` | `False` | Test-Time Augmentation (enhances quality, increases runtime) |

---

## 🤖 Model Context Protocol (MCP) Integration

Run as a native MCP server to allow AI assistants (Claude, Antigravity, Cursor) to inspect and upscale print images autonomously.

### Start MCP Server manually
```bash
upscalex-mcp
# or
upscalex serve
```

### Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "upscalex": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/upscalex",
        "upscalex-mcp"
      ]
    }
  }
}
```

### Antigravity / Cursor Configuration

Add this to your `.gemini/settings.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "upscalex": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Companies\\printing_businesses\\custom_orders\\upscalex",
        "upscalex-mcp"
      ]
    }
  }
}
```

### Exposed MCP Tools

1. `upscale_image`: Upscale any image to 16K, 8K, 4K, or custom size with model and GPU options.
2. `get_image_metadata`: Extract dimensions, aspect ratio, megapixels, and 300 DPI print measurements.
3. `list_available_models`: Inspect available RealESRGAN models.
4. `calculate_print_dpi`: Calculate effective DPI for target print dimensions and get actionable upscaling recommendations.

---

## 🧪 Running Tests

```bash
uv pip install -e ".[dev]"
pytest -v
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
