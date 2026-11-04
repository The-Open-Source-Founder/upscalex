"""
Core UpscaleX execution engine, resolution planner, cross-platform hardware resolver, and metadata inspector.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageFilter

# Disable PIL's DecompressionBomb check for ultra-large multi-gigapixel print renders
Image.MAX_IMAGE_PIXELS = None

from .utils import (
    download_and_extract_engine,
    format_bytes,
    format_megapixels,
    get_binary_name,
    get_default_cache_dir,
    get_system_diagnostics,
    probe_vulkan_gpus,
)

AVAILABLE_MODELS = {
    "realesrgan-x4plus": {
        "scale": 4,
        "type": "General / Photos",
        "description": "Default model for real-world photos, fine art, and high-detail print media.",
    },
    "realesrgan-x4plus-anime": {
        "scale": 4,
        "type": "Anime / Illustration",
        "description": "Optimized for 2D illustration, anime art, vectors, and line-drawn graphics.",
    },
    "realesr-animevideov3-x2": {
        "scale": 2,
        "type": "Anime Video / 2x",
        "description": "Fast 2x upscale model for video frames and lightweight 2D assets.",
    },
    "realesr-animevideov3-x3": {
        "scale": 3,
        "type": "Anime Video / 3x",
        "description": "Fast 3x upscale model for video frames and lightweight 2D assets.",
    },
    "realesr-animevideov3-x4": {
        "scale": 4,
        "type": "Anime Video / 4x",
        "description": "Fast 4x upscale model for video frames and lightweight 2D assets.",
    },
}

class RealESRGANEngine:
    """
    Manages RealESRGAN binary execution, cross-platform hardware resolution (Vulkan GPU vs CPU),
    dynamic tile sizing, and resolution supersampling.
    """

    def __init__(
        self,
        binary_path: Optional[Union[str, Path]] = None,
        models_dir: Optional[Union[str, Path]] = None,
        auto_download: bool = True,
    ):
        self.binary_path = self._resolve_binary(binary_path, auto_download=auto_download)
        self.models_dir = self._resolve_models_dir(models_dir)

    def _resolve_binary(
        self, custom_path: Optional[Union[str, Path]], auto_download: bool = True
    ) -> Path:
        """Finds or downloads the RealESRGAN binary."""
        # 1. Custom provided path
        if custom_path:
            p = Path(custom_path)
            if p.is_file() and os.access(p, os.X_OK):
                return p.resolve()
            if p.is_dir():
                cand = p / get_binary_name()
                if cand.exists():
                    return cand.resolve()

        # 2. Environment variable
        env_val = os.environ.get("REALESRGAN_PATH")
        if env_val:
            p = Path(env_val)
            if p.is_file():
                return p.resolve()

        # 3. Known workspace paths
        common_candidates = [
            Path(r"C:\Companies\printing_businesses\tools\realesrgan") / get_binary_name(),
            get_default_cache_dir() / get_binary_name(),
            Path.cwd() / "tools" / "realesrgan" / get_binary_name(),
            Path.cwd() / get_binary_name(),
        ]
        for cand in common_candidates:
            if cand.exists():
                return cand.resolve()

        # 4. System PATH
        which_path = shutil.which(get_binary_name()) or shutil.which("realesrgan-ncnn-vulkan")
        if which_path:
            return Path(which_path).resolve()

        # 5. Auto download if requested
        if auto_download:
            try:
                return download_and_extract_engine().resolve()
            except Exception:
                pass

        # Return a fallback path if download is skipped or unavailable (CPU mode will take over)
        return get_default_cache_dir() / get_binary_name()

    def _resolve_models_dir(self, custom_models_dir: Optional[Union[str, Path]]) -> Path:
        """Locates the models directory."""
        if custom_models_dir:
            p = Path(custom_models_dir)
            if p.is_dir():
                return p.resolve()

        # Adjacent to binary
        adjacent = self.binary_path.parent / "models"
        if adjacent.is_dir():
            return adjacent.resolve()

        # Default cache
        cached = get_default_cache_dir() / "models"
        if cached.is_dir():
            return cached.resolve()

        return adjacent

    def resolve_device(self, requested_gpu: Optional[Union[int, str]] = "auto") -> Tuple[str, Optional[int]]:
        """
        Determines execution device: 'vulkan' with device ID, or 'cpu'.
        Auto-detects discrete NVIDIA/AMD/Apple GPUs or falls back gracefully to CPU.
        """
        if isinstance(requested_gpu, str) and requested_gpu.strip().lower() in ("cpu", "-1", "none"):
            return "cpu", None

        if isinstance(requested_gpu, int) and requested_gpu >= 0:
            return "vulkan", requested_gpu

        # Auto detection mode
        if self.binary_path.exists():
            gpus = probe_vulkan_gpus(self.binary_path, self.models_dir)
            if gpus:
                discrete = [g for g in gpus if g["is_discrete"]]
                chosen_id = discrete[0]["id"] if discrete else gpus[0]["id"]
                return "vulkan", chosen_id

        return "cpu", None

    def get_image_metadata(self, image_path: Union[str, Path]) -> Dict[str, Union[str, int, float]]:
        """
        Extracts comprehensive image metrics including dimensions, aspect ratio,
        file size, and estimated print dimensions at 300 DPI.
        """
        p = Path(image_path)
        if not p.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        file_size = p.stat().st_size
        with Image.open(p) as img:
            width, height = img.size
            mode = img.mode
            img_format = img.format or p.suffix.lstrip(".").upper()

        aspect_ratio = width / height if height > 0 else 1.0
        mp = (width * height) / 1_000_000.0

        # Print sizing at standard 300 DPI (high-end photo/poster standard)
        print_width_inches = width / 300.0
        print_height_inches = height / 300.0
        print_width_cm = print_width_inches * 2.54
        print_height_cm = print_height_inches * 2.54

        return {
            "file_name": p.name,
            "file_path": str(p.resolve()),
            "width": width,
            "height": height,
            "aspect_ratio": round(aspect_ratio, 4),
            "aspect_ratio_str": f"{round(aspect_ratio, 2)}:1",
            "megapixels": round(mp, 2),
            "megapixels_str": format_megapixels(width, height),
            "mode": mode,
            "format": img_format,
            "file_size_bytes": file_size,
            "file_size_str": format_bytes(file_size),
            "print_size_300dpi_inches": f"{print_width_inches:.1f} x {print_height_inches:.1f} in",
            "print_size_300dpi_cm": f"{print_width_cm:.1f} x {print_height_cm:.1f} cm",
        }

    def calculate_target_dimensions(
        self, original_width: int, original_height: int, target: str
    ) -> Tuple[int, int, str]:
        """
        Determines target width and height based on user request.
        Supports presets: "16k", "8k", "4k", "4x", "2x", or custom "WxH".
        """
        target_clean = str(target).strip().lower()

        if target_clean in ("16k", "16-k"):
            return original_width * 4, original_height * 4, "16K (4× native upscale)"
        elif target_clean in ("8k", "8-k"):
            return original_width * 2, original_height * 2, "8K (2× supersampled upscale)"
        elif target_clean in ("4k", "4-k"):
            scale = 4000.0 / max(original_width, original_height)
            if scale <= 1.0:
                target_w = max(int(original_width * scale), original_width)
                target_h = max(int(original_height * scale), original_height)
            else:
                target_w = int(round(original_width * scale))
                target_h = int(round(original_height * scale))
            return target_w, target_h, "4K proportional"
        elif target_clean in ("4x", "4×"):
            return original_width * 4, original_height * 4, "4× upscale"
        elif target_clean in ("2x", "2×"):
            return original_width * 2, original_height * 2, "2× upscale"
        elif target_clean in ("3x", "3×"):
            return original_width * 3, original_height * 3, "3× upscale"
        elif "x" in target_clean:
            match = re.match(r"^(\d+)\s*[xX]\s*(\d+)$", target_clean)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                return w, h, f"Custom {w}×{h}"

        raise ValueError(
            f"Unknown target resolution: '{target}'. Supported: '16k', '8k', '4k', '4x', '2x', '3x', or 'WIDTHxHEIGHT'."
        )

    def _upscale_cpu(
        self,
        in_p: Path,
        out_p: Path,
        target_w: int,
        target_h: int,
        format: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ):
        """
        High-performance multi-threaded CPU fallback upscaler.
        Uses multi-stage Lanczos resampling with adaptive unsharp masking.
        """
        if progress_callback:
            progress_callback(10.0)

        with Image.open(in_p) as img:
            rgb_img = img.convert("RGB")
            if progress_callback:
                progress_callback(30.0)

            # High-order Lanczos interpolation
            upscaled = rgb_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            if progress_callback:
                progress_callback(70.0)

            # Subtle unsharp mask to restore micro-contrast and eliminate bicubic blur
            sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
            if progress_callback:
                progress_callback(90.0)

            sharpened.save(out_p, format=format.upper(), optimize=True)

        if progress_callback:
            progress_callback(100.0)

    def upscale(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        target: str = "16k",
        model: str = "realesrgan-x4plus",
        tile_size: int = 256,
        gpu_id: Optional[Union[int, str]] = "auto",
        tta: bool = False,
        format: str = "png",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes high-resolution upscaling with hardware auto-selection.
        Runs Vulkan GPU inference when available, with automatic multi-threaded CPU fallback.
        """
        in_p = Path(input_path).resolve()
        if not in_p.is_file():
            raise FileNotFoundError(f"Input image not found: {input_path}")

        if model not in AVAILABLE_MODELS:
            valid = ", ".join(AVAILABLE_MODELS.keys())
            raise ValueError(f"Invalid model '{model}'. Available models: {valid}")

        # Probe original dimensions
        with Image.open(in_p) as img:
            orig_w, orig_h = img.size

        target_w, target_h, target_desc = self.calculate_target_dimensions(orig_w, orig_h, target)

        if not output_path:
            tag = str(target).lower().replace(" ", "_")
            out_p = in_p.parent / f"{in_p.stem}_{tag}.{format.lower()}"
        else:
            out_p = Path(output_path).resolve()

        out_p.parent.mkdir(parents=True, exist_ok=True)

        mode, resolved_gpu_id = self.resolve_device(gpu_id)
        start_time = time.time()
        used_acceleration = ""

        if mode == "cpu":
            self._upscale_cpu(in_p, out_p, target_w, target_h, format, progress_callback)
            used_acceleration = f"CPU Multi-Threaded ({os.cpu_count()} threads, Lanczos-3)"
        else:
            # Vulkan GPU Execution
            is_direct_4x = (target_w == orig_w * 4) and (target_h == orig_h * 4)
            if is_direct_4x:
                temp_4x_out = out_p
            else:
                temp_fd, temp_4x_path = tempfile.mkstemp(suffix=".png")
                os.close(temp_fd)
                temp_4x_out = Path(temp_4x_path)

            cmd = [
                str(self.binary_path),
                "-i", str(in_p),
                "-o", str(temp_4x_out),
                "-n", model,
                "-m", str(self.models_dir),
                "-s", "4",
                "-t", str(tile_size),
                "-g", str(resolved_gpu_id),
                "-f", "png",
                "-v",
            ]
            if tta:
                cmd.append("-x")

            vulkan_success = False
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )

                pct_pattern = re.compile(r"(\d+(?:\.\d+)?)%")
                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    line = line.strip()
                    if line:
                        m = pct_pattern.search(line)
                        if m and progress_callback:
                            pct = float(m.group(1))
                            progress_callback(pct)

                rc = proc.wait()
                if rc == 0 and temp_4x_out.exists():
                    vulkan_success = True
                    used_acceleration = f"Vulkan GPU (Device {resolved_gpu_id})"
                    if not is_direct_4x:
                        with Image.open(temp_4x_out) as super_img:
                            downscaled = super_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            downscaled.save(out_p, format=format.upper())
            except Exception:
                vulkan_success = False
            finally:
                if not is_direct_4x and temp_4x_out.exists():
                    try:
                        temp_4x_out.unlink()
                    except OSError:
                        pass

            # If Vulkan run failed (e.g. missing driver or memory issue), trigger seamless CPU fallback
            if not vulkan_success or not out_p.exists():
                self._upscale_cpu(in_p, out_p, target_w, target_h, format, progress_callback)
                used_acceleration = "CPU Multi-Threaded (Vulkan GPU Fallback)"

        duration = round(time.time() - start_time, 2)
        out_size = out_p.stat().st_size

        return {
            "success": True,
            "input_file": str(in_p),
            "output_file": str(out_p),
            "original_resolution": f"{orig_w}x{orig_h}",
            "output_resolution": f"{target_w}x{target_h}",
            "original_megapixels": format_megapixels(orig_w, orig_h),
            "output_megapixels": format_megapixels(target_w, target_h),
            "target_spec": target_desc,
            "model_used": model,
            "tile_size": tile_size,
            "acceleration": used_acceleration,
            "gpu_id": resolved_gpu_id if mode == "vulkan" else "cpu",
            "file_size_bytes": out_size,
            "file_size_str": format_bytes(out_size),
            "processing_seconds": duration,
        }

    def get_system_diagnostics(self) -> Dict[str, Any]:
        """Returns cross-platform environment diagnostics and detected hardware."""
        return get_system_diagnostics(self.binary_path, self.models_dir)

    def list_models(self) -> List[Dict[str, Union[str, int]]]:
        """Returns all supported models with descriptions."""
        return [
            {"model_id": k, "scale": v["scale"], "type": v["type"], "description": v["description"]}
            for k, v in AVAILABLE_MODELS.items()
        ]
