# UpscaleX Installation Guide

This document provides two installation paths for UpscaleX:
1. **Agent Autonomous Setup Prompt**: A ready-to-use prompt that can be pasted into any AI coding assistant (Antigravity, Claude Code, Cursor, Windsurf) to automatically install, test, and configure the MCP server.
2. **Manual Installation Guide**: Step-by-step terminal instructions for Windows, Linux, and macOS.

See the complete guide in [`docs/installation.md`](docs/installation.md) or read the self-contained instructions below.

---

## 1. Agent Autonomous Setup Prompt

Copy and paste the following prompt directly into your AI coding assistant:

```markdown
Please install and configure the UpscaleX MCP and CLI tool in this environment.

Repository: https://github.com/The-Open-Source-Founder/upscalex.git

Instructions:
1. Verify Python 3.10+ and git are available.
2. Clone the repository into an appropriate local tools or workspace directory:
   git clone https://github.com/The-Open-Source-Founder/upscalex.git
3. Using uv (or python venv):
   - Create a virtual environment: uv venv (or python -m venv .venv)
   - Install the package in editable mode with development dependencies:
     uv pip install -e ".[dev]"
4. Execute the test suite to ensure the engine and CLI are operational:
   uv run pytest -v
5. Register the MCP server in the client configuration (e.g. claude_desktop_config.json or mcp_config.json):
   {
     "mcpServers": {
       "upscalex": {
         "command": "<ABSOLUTE_PATH_TO_VENV_PYTHON>",
         "args": ["-m", "upscalex.server"]
       }
     }
   }
6. Run "upscalex models" and report confirmation once completed.
```

---

## 2. Quick Installation via PyPI

For standalone CLI and MCP server usage, install directly via `pip`:

```bash
pip install upscalex
```

Verify the installation:
```bash
upscalex doctor
upscalex models
```

---

## 3. Manual Installation from Source

### Prerequisites

- **Python**: Version 3.10 or higher.
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `pip`.
- **GPU Driver**: Vulkan-compatible GPU drivers (NVIDIA GeForce/RTX, AMD Radeon, or Intel Arc/Iris).

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

Run pytest to verify the engine, CLI commands, and Vulkan inference:

```bash
uv run pytest -v
# Or with standard venv:
pytest -v
```

Expected result: `8 passed`.

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

Add the following entry under `"mcpServers"`:

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

#### Cursor IDE

Add to `.cursor/mcp.json` or your project settings:

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

---

### Step 6: Test Upscaling

Run a test upscale on any image:

```bash
upscalex upscale input.png --target 16k
```

Output file `input_16k.png` will be generated in the same directory.
