"""
Utility functions for UpscaleX engine, cross-platform hardware detection, downloader, and formatters.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

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
    Ensures POSIX execution permissions and clears macOS quarantine flags.
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

        # Set execution permissions on Linux/macOS
        if sys.platform != "win32" and bin_path.exists():
            bin_path.chmod(bin_path.stat().st_mode | 0o755)

        # Remove macOS quarantine flag if on Darwin
        if sys.platform == "darwin":
            try:
                subprocess.run(["xattr", "-cr", str(target_dir)], check=False, capture_output=True)
            except Exception:
                pass

        return bin_path
    finally:
        if zip_path.exists():
            try:
                zip_path.unlink()
            except OSError:
                pass

def probe_vulkan_gpus(binary_path: Path, models_dir: Path) -> List[Dict[str, Any]]:
    """
    Probes available Vulkan compute devices through the native runtime.
    Returns list of discovered GPU devices and indices.
    """
    if not binary_path.exists():
        return []

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_in:
        Image.new("RGB", (16, 16), "black").save(f_in.name)
        tmp_in = f_in.name

    tmp_out = Path(tempfile.gettempdir()) / f"probe_{os.getpid()}.png"

    try:
        cmd = [
            str(binary_path),
            "-i", tmp_in,
            "-o", str(tmp_out),
            "-m", str(models_dir),
            "-v",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        output = proc.stdout + "\n" + proc.stderr

        # Pattern matches device declarations: [0 Intel UHD], [1 NVIDIA GeForce RTX...]
        pattern = re.compile(r"\[(\d+)\s+([^\]]+)\]\s+queueC")
        devices = []
        seen = set()

        for match in pattern.finditer(output):
            dev_id = int(match.group(1))
            dev_name = match.group(2).strip()
            if dev_id not in seen:
                seen.add(dev_id)
                is_discrete = any(k in dev_name.lower() for k in ["nvidia", "geforce", "rtx", "gtx", "radeon", "rx", "apple", "discrete"])
                devices.append({
                    "id": dev_id,
                    "name": dev_name,
                    "is_discrete": is_discrete,
                })

        return devices
    except Exception:
        return []
    finally:
        for f in [Path(tmp_in), tmp_out]:
            if f.exists():
                try:
                    f.unlink()
                except OSError:
                    pass

def get_system_diagnostics(binary_path: Optional[Path] = None, models_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returns complete cross-platform environment diagnostics including
    OS, architecture, CPU threads, and detected GPU acceleration hardware.
    """
    sys_name = platform.system()
    arch = platform.machine()
    cpu_count = os.cpu_count() or 1

    gpus = []
    if binary_path and models_dir and binary_path.exists():
        gpus = probe_vulkan_gpus(binary_path, models_dir)

    # Determine recommended acceleration strategy
    if gpus:
        discrete = [g for g in gpus if g["is_discrete"]]
        selected_gpu = discrete[0]["id"] if discrete else gpus[0]["id"]
        accel_mode = f"Vulkan GPU (Device {selected_gpu}: {gpus[selected_gpu]['name']})"
        recommended_tile = 256
    else:
        selected_gpu = None
        accel_mode = f"CPU Multi-Threaded (Lanczos-3, {cpu_count} threads)"
        recommended_tile = 256

    return {
        "os": sys_name,
        "os_release": platform.release(),
        "architecture": arch,
        "python_version": platform.python_version(),
        "cpu_threads": cpu_count,
        "has_vulkan_gpu": len(gpus) > 0,
        "detected_gpus": gpus,
        "recommended_gpu_id": selected_gpu,
        "acceleration_mode": accel_mode,
        "recommended_tile_size": recommended_tile,
    }

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
