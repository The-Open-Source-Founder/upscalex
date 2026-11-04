"""
UpscaleX MCP/CLI
High-performance 8K/16K image upscaling with Vulkan GPU acceleration and Model Context Protocol.
"""

__version__ = "0.1.0"

from .engine import RealESRGANEngine
from .server import mcp

__all__ = ["RealESRGANEngine", "mcp", "__version__"]
