# UpscaleX Installation Guide

This document details installation and configuration procedures for UpscaleX across standalone environments and AI agent workflows:
1. **PyPI Package Installation**: The fastest one-command setup for CLI and MCP usage.
2. **Agent Autonomous Setup Prompt**: A copy-paste prompt for AI coding assistants (Antigravity, Claude Code, Cursor, Windsurf).
3. **Manual Source Installation**: Building and testing from the GitHub repository with `uv` or standard Python.

---

## 1. Quick Installation via PyPI

UpscaleX is published on PyPI as [`upscalex`](https://pypi.org/project/upscalex/).

```bash
pip install upscalex
```

Verify the installation:
```bash
# Inspect compute hardware and Vulkan GPU acceleration
upscalex doctor

# View the open-weight model catalog
upscalex models
```

---

## 2. Agent Autonomous Setup Prompt

Copy and paste the following prompt directly into your AI coding assistant:

```markdown
Please install and configure the UpscaleX MCP and CLI tool in this environment.

PyPI Package: https://pypi.org/project/upscalex/
Repository: https://github.com/The-Open-Source-Founder/upscalex.git

Instructions:
1. Verify Python 3.10+ is available.
2. Install UpscaleX:
   pip install upscalex
   (Or clone https://github.com/The-Open-Source-Founder/upscalex.git and install with 'uv pip install -e ".[dev]"')
3. Test hardware environment and compute engines:
   upscalex doctor
4. Register the MCP server in the client configuration (e.g. claude_desktop_config.json or mcp_config.json):
   {
     "mcpServers": {
       "upscalex": {
         "command": "upscalex-mcp"
       }
     }
   }
5. Run "upscalex models" and report confirmation once complete.
```

---

## 3. Manual Source Installation

### Prerequisites

- **Python**: Version 3.10 or higher.
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `pip`.
- **GPU Driver**: Vulkan-compatible GPU drivers (NVIDIA GeForce/RTX, AMD Radeon, or Intel Arc/Iris). Multi-threaded CPU fallback is used if no GPU is found.

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/The-Open-Source-Founder/upscalex.git
cd upscalex
```

---

### Step 2: Create a Virtual Environment and Install

#### Option A: Using `uv` (Recommended)

```bash
# Create the virtual environment
uv venv

# Install in editable mode with development dependencies
uv pip install -e ".[dev]"
```

#### Option B: Using Standard Python and Pip

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

### Step 3: Run the Verification Suite

Run pytest to verify the engine, CLI commands, model catalog, and Vulkan inference:

```bash
uv run pytest -v
# Or with standard venv:
pytest -v
```

Expected result: `17 passed`.

---

### Step 4: Verify Available Models

```bash
upscalex models
```

The tool will display the pre-trained model matrix (`realesrgan-x4plus`, `realesrgan-x4plus-anime`, etc.).

---

### Step 5: Configure the MCP Server

To enable AI agents to execute upscaling jobs autonomously, add UpscaleX to your MCP client configuration.

#### Claude Desktop

Configuration file paths:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

If installed globally via `pip`:
```json
{
  "mcpServers": {
    "upscalex": {
      "command": "upscalex-mcp"
    }
  }
}
```

If installed in an isolated `uv` virtual environment:
```json
{
  "mcpServers": {
    "upscalex": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/upscalex",
        "upscalex-mcp"
      ]
    }
  }
}
```

#### Cursor IDE & Antigravity

Add to `.cursor/mcp.json` or Antigravity's `mcp_config.json`:

```json
{
  "mcpServers": {
    "upscalex": {
      "command": "upscalex-mcp"
    }
  }
}
```

---

### Step 6: Test Upscaling

Run a test upscale on any image:

```bash
upscalex upscale input.png --target 16k
```

Output file `input_16k.png` will be generated in the same directory.

---

## 4. Troubleshooting and Recovery

For solutions to common issues (missing Vulkan drivers, CMYK auto-conversion, GPU out-of-memory errors, macOS Gatekeeper attributes), consult the comprehensive guide:
- [Error Handling and Troubleshooting Reference](troubleshooting.md)
