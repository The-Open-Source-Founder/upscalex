"""
Model Context Protocol (MCP) server for UpscaleX Ultra-High-Resolution Image Upscaling.
Integrates directly with Claude Desktop, Antigravity, Cursor, and any MCP client.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .engine import RealESRGANEngine

# Initialize the FastMCP server instance
mcp = FastMCP("UpscaleX")

_engine_instance: Optional[RealESRGANEngine] = None

def get_engine() -> RealESRGANEngine:
    """Lazy engine singleton resolver."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RealESRGANEngine(auto_download=True)
    return _engine_instance

@mcp.tool()
def upscale_image(
    image_path: str,
    target: str = "16k",
    model: str = "realesrgan-x4plus",
    output_path: Optional[str] = None,
    tile_size: int = 256,
    gpu_id: int = 1,
    tta: bool = False,
) -> Dict[str, Any]:
    """
    Upscale an image to 8K, 16K, 4x, or custom resolution using RealESRGAN.

    Args:
        image_path: Absolute or relative path to the source image (PNG, JPG, WEBP).
        target: Target resolution preset ('16k', '8k', '4k', '4x', '2x', or 'WIDTHxHEIGHT').
                Defaults to '16k' (4x upscale).
        model: RealESRGAN model ('realesrgan-x4plus' for photorealistic/print media,
               'realesrgan-x4plus-anime' for 2D art/illustrations).
        output_path: Optional path for the upscaled output. If omitted, saves next to source.
        tile_size: GPU tile size in pixels (default 256, safe for 4GB-8GB VRAM).
        gpu_id: Vulkan GPU device index (typically 1 for discrete NVIDIA GPU on laptops).
        tta: Enable Test-Time Augmentation for higher quality at the cost of speed.

    Returns:
        Dictionary containing upscale metrics, output path, final resolution, and duration.
    """
    engine = get_engine()
    return engine.upscale(
        input_path=image_path,
        output_path=output_path,
        target=target,
        model=model,
        tile_size=tile_size,
        gpu_id=gpu_id,
        tta=tta,
    )

@mcp.tool()
def get_image_metadata(image_path: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive image metadata including resolution, megapixels,
    aspect ratio, file size, color space, and print sizing at 300 DPI.

    Args:
        image_path: Path to the image file to inspect.

    Returns:
        Dictionary with image properties and print dimensions.
    """
    engine = get_engine()
    return engine.get_image_metadata(image_path)

@mcp.tool()
def list_available_models() -> List[Dict[str, Any]]:
    """
    List all supported RealESRGAN models, their scaling factor, and ideal use cases.

    Returns:
        List of model dictionaries with model_id, scale, and description.
    """
    engine = get_engine()
    return engine.list_models()

@mcp.tool()
def calculate_print_dpi(
    image_path: str,
    print_width_inches: float,
    print_height_inches: float,
) -> Dict[str, Any]:
    """
    Calculate print fidelity (DPI) for a given physical print size and recommend
    whether upscaling to 8K or 16K is required.

    Args:
        image_path: Path to the image.
        print_width_inches: Desired print width in inches (e.g. 24 for 24x36 poster).
        print_height_inches: Desired print height in inches (e.g. 36 for 24x36 poster).

    Returns:
        DPI analysis, quality rating, and recommended upscale factor.
    """
    engine = get_engine()
    meta = engine.get_image_metadata(image_path)
    w, h = meta["width"], meta["height"]

    dpi_x = w / print_width_inches if print_width_inches > 0 else 0
    dpi_y = h / print_height_inches if print_height_inches > 0 else 0
    effective_dpi = round(min(dpi_x, dpi_y), 1)

    if effective_dpi >= 300:
        quality = "Excellent (Gallery / Fine Art Quality: >=300 DPI)"
        recommendation = "No upscaling necessary for this print size."
    elif effective_dpi >= 200:
        quality = "Good (Standard Commercial Print: 200-299 DPI)"
        recommendation = "Upscaling to 8K or 2x recommended for fine text and sharp lines."
    elif effective_dpi >= 150:
        quality = "Fair (Acceptable viewing distance print: 150-199 DPI)"
        recommendation = "Upscaling to 8K or 16K strongly recommended for sharp print detail."
    else:
        quality = "Poor (Pixelated / Low Resolution: <150 DPI)"
        recommendation = "Upscaling to 16K (4x) required to avoid visible pixelation and blurring."

    return {
        "image_path": str(image_path),
        "current_resolution": f"{w}x{h}",
        "print_size_inches": f"{print_width_inches} x {print_height_inches}",
        "effective_dpi": effective_dpi,
        "quality_rating": quality,
        "recommendation": recommendation,
    }

def main():
    """Run MCP server via stdio transport."""
    mcp.run()

if __name__ == "__main__":
    main()
