"""
Rich interactive CLI interface for UpscaleX image upscaling and MCP management.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .engine import AVAILABLE_MODELS, RealESRGANEngine
from .server import mcp
from .utils import download_and_extract_engine, get_system_diagnostics

console = Console()

@click.group()
@click.version_option(package_name="upscalex")
def main():
    """UpscaleX MCP/CLI: Production-grade 8K/16K RealESRGAN Image Upscaler & MCP Server."""
    pass

@main.command()
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-t", "--target",
    default="16k",
    help="Target resolution: '16k' (4x), '8k' (2x supersampled), '4k', '4x', '2x', or 'WxH'.",
    show_default=True,
)
@click.option(
    "-m", "--model",
    default="realesrgan-x4plus",
    type=click.Choice(list(AVAILABLE_MODELS.keys()), case_sensitive=False),
    help="RealESRGAN model to apply.",
    show_default=True,
)
@click.option("-o", "--output", default=None, help="Output destination file path.")
@click.option("--tile-size", default=256, type=int, help="GPU tile size in pixels (safe for 4GB VRAM).", show_default=True)
@click.option("-g", "--gpu-id", default="auto", type=str, help="Vulkan GPU device index ('auto', integer ID, or 'cpu').", show_default=True)
@click.option("-x", "--tta", is_flag=True, default=False, help="Enable Test-Time Augmentation (higher quality, slower).")
def upscale(
    image_path: str,
    target: str,
    model: str,
    output: Optional[str],
    tile_size: int,
    gpu_id: str,
    tta: bool,
):
    """Upscale an image to 8K, 16K, or custom print resolutions."""
    try:
        engine = RealESRGANEngine(auto_download=True)
        meta = engine.get_image_metadata(image_path)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        sys.exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]Input:[/bold cyan] {meta['file_name']}\n"
            f"[bold cyan]Original Resolution:[/bold cyan] {meta['width']} × {meta['height']} ({meta['megapixels_str']})\n"
            f"[bold cyan]Target Mode:[/bold cyan] [bold green]{target.upper()}[/bold green]\n"
            f"[bold cyan]Model:[/bold cyan] {model} | [bold cyan]Hardware:[/bold cyan] {gpu_id} | [bold cyan]Tile Size:[/bold cyan] {tile_size}px",
            title="[bold yellow]UpscaleX CLI[/bold yellow]",
            border_style="cyan",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[bold yellow]{task.percentage:>3.1f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Processing tiles...", total=100.0)

        def on_progress(pct: float):
            progress.update(task_id, completed=pct)

        try:
            result = engine.upscale(
                input_path=image_path,
                output_path=output,
                target=target,
                model=model,
                tile_size=tile_size,
                gpu_id=gpu_id,
                tta=tta,
                progress_callback=on_progress,
            )
            progress.update(task_id, completed=100.0)
        except Exception as e:
            console.print(f"\n[bold red]Upscaling Failed:[/bold red] {e}")
            sys.exit(1)

    # Render results table
    table = Table(title="Upscale Completed Successfully", border_style="green", header_style="bold green")
    table.add_column("Property", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Output File", result["output_file"])
    table.add_row("Final Resolution", f"{result['output_resolution']} ({result['output_megapixels']})")
    table.add_row("Resolution Gain", f"{result['original_megapixels']} -> {result['output_megapixels']}")
    table.add_row("File Size", f"{result['file_size_str']}")
    table.add_row("Acceleration", f"{result['acceleration']}")
    table.add_row("Duration", f"{result['processing_seconds']} seconds")
    table.add_row("Model Used", str(result["model_used"]))

    console.print(table)

@main.command()
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False))
def info(image_path: str):
    """Inspect image resolution, aspect ratio, file size, and print dimensions at 300 DPI."""
    try:
        engine = RealESRGANEngine(auto_download=False)
    except Exception:
        engine = None

    if engine:
        meta = engine.get_image_metadata(image_path)
    else:
        from PIL import Image
        from .utils import format_bytes, format_megapixels
        p = Path(image_path)
        with Image.open(p) as img:
            w, h = img.size
            mode = img.mode
            fmt = img.format
        meta = {
            "file_name": p.name,
            "file_path": str(p.resolve()),
            "width": w,
            "height": h,
            "aspect_ratio": round(w / h, 4) if h else 1.0,
            "megapixels_str": format_megapixels(w, h),
            "mode": mode,
            "format": fmt,
            "file_size_str": format_bytes(p.stat().st_size),
            "print_size_300dpi_inches": f"{w / 300.0:.1f} x {h / 300.0:.1f} in",
            "print_size_300dpi_cm": f"{(w / 300.0) * 2.54:.1f} x {(h / 300.0) * 2.54:.1f} cm",
        }

    table = Table(title=f"Image Metadata: {meta['file_name']}", border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value", style="yellow")

    table.add_row("Dimensions", f"{meta['width']} × {meta['height']}")
    table.add_row("Megapixels", str(meta['megapixels_str']))
    table.add_row("Aspect Ratio", f"{meta['aspect_ratio']} (W:H)")
    table.add_row("Color Mode", str(meta['mode']))
    table.add_row("Format", str(meta['format']))
    table.add_row("File Size", str(meta['file_size_str']))
    table.add_row("Print Size (300 DPI)", str(meta['print_size_300dpi_inches']))
    table.add_row("Print Size (Metric)", str(meta['print_size_300dpi_cm']))

    console.print(table)

@main.command()
def doctor():
    """Inspect cross-platform system environment, CPU threads, and GPU acceleration hardware."""
    try:
        engine = RealESRGANEngine(auto_download=False)
        diag = engine.get_system_diagnostics()
    except Exception:
        diag = get_system_diagnostics()

    table = Table(title="UpscaleX System & Hardware Diagnostics", border_style="blue", header_style="bold blue")
    table.add_column("Component", style="bold")
    table.add_column("Details", style="cyan")

    table.add_row("Operating System", f"{diag['os']} ({diag['os_release']})")
    table.add_row("Architecture", diag['architecture'])
    table.add_row("Python Version", diag['python_version'])
    table.add_row("CPU Logical Cores", str(diag['cpu_threads']))
    table.add_row("Vulkan GPU Available", "Yes" if diag['has_vulkan_gpu'] else "No (CPU Multi-Threaded Mode)")

    if diag['detected_gpus']:
        for g in diag['detected_gpus']:
            marker = " (Discrete / Default)" if g['id'] == diag.get('recommended_gpu_id') else ""
            table.add_row(f"GPU [{g['id']}]", f"{g['name']}{marker}")
    else:
        table.add_row("GPU Devices", "None detected (Headless or CPU-only environment)")

    table.add_row("Default Mode", diag['acceleration_mode'])
    table.add_row("Recommended Tile Size", f"{diag['recommended_tile_size']}px")

    console.print(table)

@main.command()
def models():
    """List all available RealESRGAN pre-trained models."""
    table = Table(title="Available RealESRGAN Models", border_style="magenta", header_style="bold magenta")
    table.add_column("Model ID", style="bold cyan")
    table.add_column("Scale", style="green")
    table.add_column("Target Media", style="yellow")
    table.add_column("Description", style="white")

    for k, v in AVAILABLE_MODELS.items():
        table.add_row(k, f"{v['scale']}×", v["type"], v["description"])

    console.print(table)

@main.command()
def download_engine():
    """Download and set up the official Real-ESRGAN Vulkan engine binary."""
    console.print("[cyan]Checking Real-ESRGAN binary status...[/cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading pre-compiled engine...", total=100.0)

        def cb(downloaded: int, total: int):
            if total > 0:
                pct = (downloaded / total) * 100.0
                progress.update(task, completed=min(pct, 100.0))

        bin_path = download_and_extract_engine(progress_callback=cb)
        progress.update(task, completed=100.0)

    console.print(f"[bold green]Engine ready at:[/bold green] {bin_path}")

@main.command()
def serve():
    """Start the Model Context Protocol (MCP) server over standard I/O."""
    console.print("[bold green]Starting UpscaleX MCP Server on stdio...[/bold green]", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()
