"""
Rich interactive CLI interface for UpscaleX image upscaling, model catalog, and MCP management.
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

from .engine import MODEL_CATALOG, RealESRGANEngine
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
    type=click.Choice(list(MODEL_CATALOG.keys()), case_sensitive=False),
    help="Model identifier to apply.",
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
def recommend(image_path: str):
    """Recommend the optimal model, target resolution, and tile size for an image based on system hardware."""
    try:
        engine = RealESRGANEngine(auto_download=False)
        rec = engine.recommend_model(image_path)
    except Exception as e:
        console.print(f"[bold red]Recommendation Error:[/bold red] {e}")
        sys.exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]Input Image:[/bold cyan] {rec['file_name']}\n"
            f"[bold cyan]Content Type:[/bold cyan] [bold green]{rec['detected_content_type']}[/bold green]\n"
            f"[bold cyan]Hardware Tier:[/bold cyan] [bold yellow]{rec['hardware_tier']}[/bold yellow]\n"
            f"[bold cyan]Recommended Model:[/bold cyan] [bold white]{rec['recommended_model']}[/bold white]\n"
            f"[bold cyan]Recommended Target:[/bold cyan] [bold green]{rec['recommended_target'].upper()}[/bold green]\n"
            f"[bold cyan]Recommended Tile Size:[/bold cyan] {rec['recommended_tile_size']}px\n\n"
            f"[bold cyan]Model Selection Reasoning:[/bold cyan]\n{rec['model_selection_reasoning']}\n\n"
            f"[bold cyan]Resolution Reasoning:[/bold cyan]\n{rec['target_resolution_reasoning']}\n\n"
            f"[bold cyan]Ready-to-Run Command:[/bold cyan]\n[bold green]{rec['ready_command']}[/bold green]",
            title="[bold yellow]UpscaleX Smart Recommendation Engine[/bold yellow]",
            border_style="yellow",
        )
    )

@main.command()
@click.argument("model_id")
def download_model(model_id: str):
    """Download an open-weight model from the catalog into local storage."""
    try:
        engine = RealESRGANEngine(auto_download=False)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        sys.exit(1)

    if model_id not in MODEL_CATALOG:
        valid = ", ".join(MODEL_CATALOG.keys())
        console.print(f"[bold red]Unknown model:[/bold red] {model_id}\n[cyan]Catalog models:[/cyan] {valid}")
        sys.exit(1)

    meta = MODEL_CATALOG[model_id]
    console.print(f"[cyan]Downloading model:[/cyan] [bold]{meta['name']}[/bold] ({meta['type']})")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[bold yellow]{task.percentage:>3.1f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching weights...", total=100.0)

        def cb(downloaded: int, total: int):
            if total > 0:
                pct = (downloaded / total) * 100.0
                progress.update(task, completed=min(pct, 100.0))

        try:
            res = engine.download_model(model_id, progress_callback=cb)
            progress.update(task, completed=100.0)
        except Exception as e:
            console.print(f"\n[bold red]Download Failed:[/bold red] {e}")
            sys.exit(1)

    console.print(f"[bold green]{res['message']}[/bold green] ([cyan]{res.get('size_str', 'ready')}[/cyan])")

@main.command()
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False))
def info(image_path: str):
    """Inspect image resolution, aspect ratio, file size, and print dimensions at 300 DPI."""
    try:
        engine = RealESRGANEngine(auto_download=False)
        meta = engine.get_image_metadata(image_path)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

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
    """List all supported models with VRAM requirements, target media, and local status."""
    try:
        engine = RealESRGANEngine(auto_download=False)
        model_list = engine.list_models()
    except Exception:
        model_list = []

    table = Table(title="UpscaleX Model Catalog & VRAM Requirements", border_style="magenta", header_style="bold magenta")
    table.add_column("Model ID", style="bold cyan")
    table.add_column("Scale", style="green")
    table.add_column("Target Media", style="yellow")
    table.add_column("VRAM Requirement", style="white")
    table.add_column("Status", style="bold")

    for m in model_list:
        status_text = "[green]Installed[/green]" if m["installed"] else "[dim yellow]Available for download[/dim yellow]"
        table.add_row(m["model_id"], f"{m['scale']}×", m["type"], m["vram_tier"], status_text)

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
