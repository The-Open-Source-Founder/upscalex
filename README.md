# UpscaleX MCP/CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP: Enabled](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Acceleration: Vulkan GPU](https://img.shields.io/badge/Acceleration-Vulkan%20GPU-orange.svg)](https://www.khronos.org/vulkan/)

UpscaleX is a production-grade 8K and 16K image upscaler CLI and Model Context Protocol (MCP) server powered by RealESRGAN, Vulkan GPU hardware acceleration, and Lanczos supersampling.

Engineered for digital print workflows, large-format poster production, fine art reproductions, and autonomous AI coding agents in Claude Desktop, Antigravity, and Cursor.

---

## Table of Contents

- [Key Features](#key-features)
- [Documentation Directory](#documentation-directory)
- [Quickstart with uv](#quickstart-with-uv)
- [Command-Line Interface](#command-line-interface)
- [Model Context Protocol (MCP) Integration](#model-context-protocol-mcp-integration)
- [Model Matrix](#model-matrix)
- [Testing and Verification](#testing-and-verification)
- [Contributing](#contributing)
- [License](#license)

---

## Key Features

- **Dual-Mode Operation**: Interactive command-line interface (`upscalex`) and standard Model Context Protocol server (`upscalex-mcp`).
- **8K and 16K Presets**:
  - **16K**: Native 4x RealESRGAN deep-learning model upscale producing master files up to 400+ Megapixels.
  - **8K**: 4x deep-learning inference followed by Lanczos-3 downsampling (Supersampling Anti-Aliasing / SSAA) for sharp edges and zero noise.
  - **Custom Dimensions**: Proportional scaling to arbitrary resolutions or physical print aspect ratios.
- **Vulkan Hardware Acceleration**: High-performance C++ inference across NVIDIA, AMD, and Intel GPUs without compiling CUDA wheels.
- **Memory-Safe Tiling**: Sliding-window spatial tile decomposition (`--tile-size 256`) processes ultra-gigapixel images without Out-Of-Memory (OOM) failures on 4GB to 8GB GPUs.
- **Automated Engine Provisioning**: Downloads and validates the precompiled platform binary automatically if not found locally.
- **Print Fidelity Analysis**: Automatically calculates physical print dimensions in inches and centimeters at 300 DPI, 150 DPI, and 72 DPI.

---

## Documentation Directory

Comprehensive technical guides are available in the [`docs/`](docs/) directory:

- [CLI Reference Guide](docs/cli-guide.md): Complete flag documentation, tiling strategies, and execution examples.
- [Model Context Protocol (MCP) Guide](docs/mcp-guide.md): JSON-RPC tool contracts, parameter schemas, and multi-client configuration.
- [Architecture & Mathematics Specification](docs/architecture.md): Deep-learning foundations, RRDB networks, Lanczos kernels, and memory bounds.
- [Contributing Guide](CONTRIBUTING.md): Code standards, test procedures, and pull request workflow.

---

## Quickstart with uv

### Installation

Clone the repository and install using [`uv`](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/The-Open-Source-Founder/upscalex.git
cd upscalex

# Create virtual environment and install package
uv venv
uv pip install -e .
```

### Inspect Available Models

```bash
upscalex models
```

---

## Command-Line Interface

### 16K Upscale (Default 4x Model)

```bash
upscalex upscale input.png --target 16k
```

### 8K Supersampled Upscale

```bash
upscalex upscale poster.png --target 8k -o poster_8k.png
```

### 2D Illustration / Anime Artwork

```bash
upscalex upscale graphic.png --model realesrgan-x4plus-anime --target 8k
```

### Image and Print Sizing Inspection

```bash
upscalex info input.png
```

For complete options and arguments, see the [CLI Guide](docs/cli-guide.md).

---

## Model Context Protocol (MCP) Integration

UpscaleX runs as a native MCP server, enabling LLM agents to inspect image properties, evaluate print viability, and execute upscaling autonomously.

### Server Invocation

```bash
upscalex-mcp
# or
upscalex serve
```

### Client Configuration

Add this entry to your MCP client configuration file:

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

Detailed configuration instructions for Claude Desktop, Antigravity, and Cursor are provided in the [MCP Guide](docs/mcp-guide.md).

---

## Model Matrix

| Model ID | Native Scale | Target Media | Application |
| :--- | :--- | :--- | :--- |
| `realesrgan-x4plus` | 4x | General / Photography | Default model for real-world photos, fine art, textures, and print posters. |
| `realesrgan-x4plus-anime` | 4x | Anime / Illustration | Optimized for digital art, vector illustrations, line work, and comics. |
| `realesr-animevideov3-x2` | 2x | Animation / Video | Rapid 2x turnaround model for video frames and lightweight 2D assets. |
| `realesr-animevideov3-x3` | 3x | Animation / Video | Rapid 3x turnaround model for video frames and lightweight 2D assets. |
| `realesr-animevideov3-x4` | 4x | Animation / Video | Rapid 4x turnaround model for video frames and lightweight 2D assets. |

---

## Testing and Verification

Run the test suite to verify model resolution calculation, CLI exit codes, and live GPU inference:

```bash
uv pip install -e ".[dev]"
uv run pytest -v
```

All tests must pass prior to submitting changes.

---

## Contributing

Contributions to UpscaleX are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards, pull request processes, and development guidelines.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
