# Contributing to UpscaleX

Thank you for your interest in contributing to UpscaleX. This project maintains a strict engineering standard focused on high-performance image processing, robust CLI ergonomics, and reliable Model Context Protocol (MCP) server integration.

All contributions, whether bug fixes, documentation improvements, model integrations, or architectural enhancements, are welcome.

---

## Code of Conduct

Contributors are expected to adhere to professional communication and collaboration standards:
- Maintain technical, constructive, and objective dialogue in issues and pull requests.
- Respect differing perspectives and technical approaches.
- Focus on performance, memory safety, test coverage, and documentation accuracy.

---

## Development Environment Setup

UpscaleX uses [`uv`](https://github.com/astral-sh/uv) as its package manager and execution environment.

### Prerequisites

- Python 3.10 or later
- Vulkan-compatible GPU (NVIDIA, AMD, or Intel) with up-to-date graphics drivers
- Git

### Initializing the Workspace

1. Fork the repository on GitHub and clone your fork:
   ```bash
   git clone https://github.com/<your-username>/upscalex.git
   cd upscalex
   ```

2. Create a virtual environment using `uv`:
   ```bash
   uv venv
   ```

3. Install editable dependencies, including development tools:
   ```bash
   uv pip install -e ".[dev]"
   ```

4. Verify your setup by running the test suite:
   ```bash
   uv run pytest -v
   ```

---

## Project Structure

```
upscalex/
├── src/
│   └── upscalex/
│       ├── __init__.py       # Package initialization and public API
│       ├── cli.py            # Command-line interface implementation
│       ├── engine.py         # Subprocess runner, tiling logic, Lanczos resampler
│       ├── server.py         # FastMCP server and tool registrations
│       └── utils.py          # Binary fetcher, platform resolvers, formatters
├── tests/
│   ├── test_cli.py           # CLI invocation and runner tests
│   └── test_engine.py        # Core processing, mathematical sizing, and GPU tests
├── docs/                     # Technical documentation
│   ├── architecture.md       # Pipeline architecture and memory management
│   ├── cli-guide.md          # Command-line interface reference
│   └── mcp-guide.md          # Model Context Protocol integration reference
├── pyproject.toml            # PEP 621 package metadata and entry points
├── uv.lock                   # Pinned dependency lockfile
└── LICENSE                   # MIT License
```

---

## Coding Standards

### Python Style

- Adhere to PEP 8 standards with modern typing annotations (`from __future__ import annotations`).
- Ensure all public functions, classes, and methods have comprehensive docstrings explaining arguments, return types, and exceptions raised.
- Avoid emoji usage in commit messages, documentation, terminal outputs, and code comments. Maintain a clean, professional technical tone.
- Do not introduce dependencies that require CUDA compilation unless behind optional build flags. The core engine relies on Vulkan runtime binaries.

### Memory & Stability Rules

- When interacting with high-resolution image decoders (such as Pillow), always account for ultra-large resolutions exceeding 100 Megapixels.
- Set `Image.MAX_IMAGE_PIXELS = None` in modules handling raw bitmaps to avoid decompression bomb exceptions during multi-gigapixel print jobs.
- Always guarantee temporary files created during supersampling or tile processing are safely unlinked in `finally` blocks.

---

## Testing Workflow

All pull requests must maintain 100% pass rate on existing and new tests.

Run tests locally using pytest:
```bash
uv run pytest -v
```

When contributing new features:
1. Add corresponding unit tests in `tests/test_engine.py` or `tests/test_cli.py`.
2. Verify that CLI commands exit with code `0` on success and appropriate non-zero error codes on failure.
3. Test edge cases such as missing binaries, invalid image paths, non-standard aspect ratios, and extreme resolutions.

---

## Pull Request Process

1. Create a descriptive feature branch from `main`:
   ```bash
   git checkout -b feature/tiling-optimization
   ```

2. Format commits using Conventional Commit style:
   - `feat: add support for custom tile padding`
   - `fix: handle missing models directory in custom paths`
   - `docs: update mcp configuration guide for cursor`
   - `perf: optimize memory consumption during lanczos downscaling`

3. Ensure `uv.lock` is kept up to date if dependencies are modified:
   ```bash
   uv lock
   ```

4. Push your branch to your fork and submit a Pull Request against the `main` branch.
5. Provide a clear summary in your pull request description detailing:
   - The rationale for the change.
   - Any benchmarks or performance impacts.
   - Verification steps taken.
