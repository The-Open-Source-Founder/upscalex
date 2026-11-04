"""
Utility functions for RealESRGAN engine, downloader, and formatters.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

# Official Real-ESRGAN release binary URLs
RELEASE_URLS = {
    "Windows": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",
    "Linux": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip",
    "Darwin": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip",
}

def get_default_cache_dir() -> Path:
    """Returns the platform-appropriate cache directory for binary storage."""
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "realesrgan-upscaler"
        return home / ".cache" / "realesrgan-upscaler"
    elif sys.platform == "darwin":
        return home / "Library" / "Caches" / "realesrgan-upscaler"
    else:
        return home / ".cache" / "realesrgan-upscaler"

def get_binary_name() -> str:
    """Returns the executable name for the current OS."""
    return "realesrgan-ncnn-vulkan.exe" if sys.platform == "win32" else "realesrgan-ncnn-vulkan"

def download_and_extract_engine(dest_dir: Optional[Path] = None, progress_callback = None) -> Path:
    """
    Downloads and extracts the official pre-compiled Real-ESRGAN binary.
    Returns the path to the executable.
    """
    system_name = platform.system()
    if system_name not in RELEASE_URLS:
        raise RuntimeError(f"Unsupported operating system for precompiled binary: {system_name}")

    url = RELEASE_URLS[system_name]
    target_dir = dest_dir or get_default_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    bin_name = get_binary_name()
    bin_path = target_dir / bin_name

    if bin_path.exists() and (target_dir / "models").exists():
        return bin_path

    zip_path = target_dir / "realesrgan.zip"

    try:
        def reporthook(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                progress_callback(block_num * block_size, total_size)

        urllib.request.urlretrieve(url, zip_path, reporthook=reporthook)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

        # Ensure executable permissions on POSIX
        if sys.platform != "win32" and bin_path.exists():
            bin_path.chmod(bin_path.stat().st_mode | 0o755)

        return bin_path
    finally:
        if zip_path.exists():
            try:
                zip_path.unlink()
            except OSError:
                pass

def format_bytes(size: int | float) -> str:
    """Format bytes into a human-readable string (KB, MB, GB)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(size)
    for u in units:
        if val < 1024.0 or u == "TB":
            return f"{val:.2f} {u}"
        val /= 1024.0
    return f"{size} B"

def format_megapixels(width: int, height: int) -> str:
    """Calculates megapixels and formats as string."""
    mp = (width * height) / 1_000_000.0
    return f"{mp:.2f} MP"
