# UpscaleX Model Context Protocol (MCP) Guide

This document details the architecture, tools, and integration procedures for running UpscaleX as a Model Context Protocol (MCP) server.

---

## Architecture Overview

UpscaleX implements the [Model Context Protocol](https://modelcontextprotocol.io) using the `fastmcp` framework over standard input/output (`stdio`).

This allows Large Language Model (LLM) agents—such as Claude Desktop, Cursor, Antigravity, and autonomous workflow orchestrators—to inspect image resolutions, calculate print viability, and execute hardware-accelerated upscaling jobs without leaving the conversational interface.

```
+-------------------------------------------------------------+
|                     AI Agent / MCP Client                   |
|              (Claude Desktop, Antigravity, Cursor)          |
+-------------------------------------------------------------+
                              |
                     Standard I/O (JSON-RPC)
                              |
                              v
+-------------------------------------------------------------+
|                      UpscaleX MCP Server                    |
|                         (upscalex-mcp)                      |
+-------------------------------------------------------------+
       |                      |                       |
       v                      v                       v
+--------------+      +----------------+      +---------------+
| Image Meta   |      | RealESRGAN     |      | Lanczos-3     |
| Inspector    |      | Vulkan Engine  |      | Supersampling |
+--------------+      +----------------+      +---------------+
```

---

## Server Executable

The MCP server can be invoked using either of the following commands:

```bash
# Direct entrypoint
upscalex-mcp

# Or via the CLI runner
upscalex serve
```

---

## Exposed MCP Tools

The server registers six primary tools under standard JSON-RPC contracts:

1. `upscale_image`: Execute deep-learning upscaling with resolution presets and hardware selection.
2. `recommend_model`: Analyze image characteristics and host specs to recommend optimal model, target, and tiling.
3. `download_model`: Download open-weight models on demand from upstream mirrors into local storage.
4. `get_image_metadata`: Inspect dimensions, aspect ratio, megapixels, color space, and 300 DPI print measurements.
5. `list_available_models`: Inspect model catalog, VRAM tiers, and local installation status.
6. `calculate_print_dpi`: Calculate effective DPI and suitability for specific poster/canvas print dimensions.

Executes deep-learning upscaling on an input image file.

#### Parameters

| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `image_path` | `string` | Yes | — | Absolute or relative path to the source image file. |
| `target` | `string` | No | `"16k"` | Resolution preset: `"16k"`, `"8k"`, `"4k"`, `"4x"`, `"2x"`, or `"WIDTHxHEIGHT"`. |
| `model` | `string` | No | `"realesrgan-x4plus"` | Model ID: `"realesrgan-x4plus"` (photos/prints) or `"realesrgan-x4plus-anime"` (illustrations). |
| `output_path` | `string` | No | `null` | Target output path. If omitted, saves alongside original with resolution suffix. |
| `tile_size` | `integer` | No | `256` | GPU tile dimension in pixels to control VRAM usage. |
| `gpu_id` | `integer` | No | `1` | Vulkan device index (`1` for discrete GPU on multi-GPU systems). |
| `tta` | `boolean` | No | `false` | Enable Test-Time Augmentation (8-pass rotational inference). |

#### Return Object

```json
{
  "success": true,
  "input_file": "C:\\path\\to\\source.png",
  "output_file": "C:\\path\\to\\source_16k.png",
  "original_resolution": "4024x6252",
  "output_resolution": "16096x25008",
  "original_megapixels": "25.16 MP",
  "output_megapixels": "402.53 MP",
  "target_spec": "16K (4× native upscale)",
  "model_used": "realesrgan-x4plus",
  "tile_size": 256,
  "gpu_id": 1,
  "file_size_bytes": 472833076,
  "file_size_str": "450.93 MB",
  "processing_seconds": 182.4
}
```

---

### 2. `recommend_model`

Evaluates host GPU VRAM, CPU cores, image resolution, and visual entropy (photos vs 2D illustrations) to recommend the optimal model, resolution target, and tile size.

#### Parameters

| Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `image_path` | `string` | Yes | — | Absolute or relative path to the image file. |
| `priority` | `string` | No | `"balanced"` | Optimization priority: `"balanced"`, `"speed"`, or `"quality"`. |

#### Return Object

```json
{
  "image_path": "C:\\images\\source.png",
  "file_name": "source.png",
  "detected_content_type": "Photographic / Continuous Tone / Fine Art",
  "hardware_tier": "Dedicated GPU (NVIDIA GeForce RTX 3050 Laptop GPU)",
  "recommended_model": "realesrgan-x4plus",
  "recommended_target": "16k",
  "recommended_tile_size": 256,
  "recommended_gpu_id": "auto",
  "target_resolution_reasoning": "Source image is >=20 MP. Native 16K (4x) upscale is ideal for large-format exhibition master prints.",
  "model_selection_reasoning": "Detected Photographic art on NVIDIA GeForce RTX 3050. 'realesrgan-x4plus' with 256px tiling delivers pristine textural and fine-art fidelity.",
  "ready_command": "upscalex upscale \"source.png\" --target 16k --model realesrgan-x4plus --tile-size 256",
  "is_model_installed": true
}
```

---

### 3. `download_model`

Downloads open-weight model files on demand from upstream mirrors into local storage.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `model_id` | `string` | Yes | Model ID to download (e.g. `'4x-ultrasharp'`, `'4x-nmkd-superscale'`, `'realesr-general-x4v3'`). |

#### Return Object

```json
{
  "success": true,
  "model_id": "4x-ultrasharp",
  "name": "4x UltraSharp (Community Edition)",
  "status": "downloaded",
  "message": "Model '4x UltraSharp (Community Edition)' successfully downloaded.",
  "size_str": "67.04 MB"
}
```

---

### 4. `get_image_metadata`

Inspects pixel dimensions, color channels, format, and physical print dimensions at 300 DPI.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `image_path` | `string` | Yes | Absolute or relative path to the image file. |

#### Return Object

```json
{
  "file_name": "client_artwork.png",
  "file_path": "C:\\images\\client_artwork.png",
  "width": 4024,
  "height": 6252,
  "aspect_ratio": 0.6436,
  "aspect_ratio_str": "0.64:1",
  "megapixels": 25.16,
  "megapixels_str": "25.16 MP",
  "mode": "RGB",
  "format": "PNG",
  "file_size_bytes": 30589040,
  "file_size_str": "29.17 MB",
  "print_size_300dpi_inches": "13.4 x 20.8 in",
  "print_size_300dpi_cm": "34.1 x 52.9 cm"
}
```

---

### 3. `list_available_models`

Enumerates all pre-trained weights, scale capabilities, and recommended target media.

#### Parameters
None.

#### Return Object

```json
[
  {
    "model_id": "realesrgan-x4plus",
    "scale": 4,
    "type": "General / Photos",
    "description": "Default model for real-world photos, fine art, and high-detail print media."
  },
  {
    "model_id": "realesrgan-x4plus-anime",
    "scale": 4,
    "type": "Anime / Illustration",
    "description": "Optimized for 2D illustration, anime art, vectors, and line-drawn graphics."
  }
]
```

---

### 4. `calculate_print_dpi`

Evaluates physical print fidelity for specific poster or canvas dimensions and provides actionable upscale recommendations.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `image_path` | `string` | Yes | Path to the image file. |
| `print_width_inches` | `number` | Yes | Desired physical print width in inches (e.g. `24` for 24x36 poster). |
| `print_height_inches` | `number` | Yes | Desired physical print height in inches (e.g. `36` for 24x36 poster). |

#### Return Object

```json
{
  "image_path": "C:\\images\\source.png",
  "current_resolution": "4024x6252",
  "print_size_inches": "24 x 36",
  "effective_dpi": 167.7,
  "quality_rating": "Fair (Acceptable viewing distance print: 150-199 DPI)",
  "recommendation": "Upscaling to 8K or 16K strongly recommended for sharp print detail."
}
```

---

## Client Integration Configurations

### Claude Desktop

Edit your `claude_desktop_config.json`:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

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

### Cursor IDE

Add to `.cursor/mcp.json` or global cursor MCP configuration:

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

---

## Protocol Diagnostic & Error Handling

- **Decompression Bomb Protection**: UpscaleX disables PIL's default pixel count limits internally (`Image.MAX_IMAGE_PIXELS = None`), preventing crashes when decoding multi-hundred-megabyte bitmaps.
- **Stderr Logging**: All diagnostic and progress logs are routed to `stderr`. Only valid JSON-RPC frames are transmitted over `stdout`, preventing protocol parse desynchronization.
