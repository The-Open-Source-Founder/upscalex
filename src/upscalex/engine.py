"""
Core RealESRGAN execution engine, resolution planner, and metadata inspector.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from PIL import Image

# Disable PIL's DecompressionBomb check for ultra-large multi-gigapixel print renders
Image.MAX_IMAGE_PIXELS = None

from .utils import (
    download_and_extract_engine,
    format_bytes,
    format_megapixels,
    get_binary_name,
    get_default_cache_dir,
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
    Manages the RealESRGAN binary execution, model validation,
    supersampled resolution scaling, and image metadata parsing.
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
            return download_and_extract_engine().resolve()

        raise FileNotFoundError(
            f"Real-ESRGAN binary ({get_binary_name()}) not found. "
            f"Specify binary_path or set REALESRGAN_PATH environment variable."
        )

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
        target_clean = target.strip().lower()

        if target_clean in ("16k", "16-k"):
            # 4x of ~4K base or 4x proportional
            return original_width * 4, original_height * 4, "16K (4× native upscale)"
        elif target_clean in ("8k", "8-k"):
            # 2x proportional
            return original_width * 2, original_height * 2, "8K (2× supersampled upscale)"
        elif target_clean in ("4k", "4-k"):
            # Standard 4K proportional target
            scale = 4000.0 / max(original_width, original_height)
            if scale <= 1.0:
                # If image is already 4K+, keep or 1x
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

    def upscale(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        target: str = "16k",
        model: str = "realesrgan-x4plus",
        tile_size: int = 256,
        gpu_id: int = 1,
        tta: bool = False,
        format: str = "png",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Union[str, int, float, bool]]:
        """
        Executes high-resolution RealESRGAN upscaling.
        If target is smaller than 4x (e.g. 8K or 2x), the 4x RealESRGAN model is executed
        and then downscaled via high-order Lanczos resampling for pristine anti-aliased sharpness.
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

        # Decide default output path if not specified
        if not output_path:
            tag = target.lower().replace(" ", "_")
            out_p = in_p.parent / f"{in_p.stem}_{tag}.{format.lower()}"
        else:
            out_p = Path(output_path).resolve()

        out_p.parent.mkdir(parents=True, exist_ok=True)

        is_direct_4x = (target_w == orig_w * 4) and (target_h == orig_h * 4)
        start_time = time.time()

        # Temporary file path if supersampling is needed
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
            "-g", str(gpu_id),
            "-f", "png",
            "-v",
        ]
        if tta:
            cmd.append("-x")

        try:
            # Run the engine process
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Monitor progress
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
            if rc != 0:
                raise RuntimeError(f"Real-ESRGAN failed with return code {rc}")

            if not temp_4x_out.exists():
                raise FileNotFoundError(f"Expected Real-ESRGAN output was not created: {temp_4x_out}")

            # If supersampling is required (e.g. 8k, 2x, or custom)
            if not is_direct_4x:
                with Image.open(temp_4x_out) as super_img:
                    downscaled = super_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    downscaled.save(out_p, format=format.upper())
                try:
                    temp_4x_out.unlink()
                except OSError:
                    pass

        finally:
            if not is_direct_4x and temp_4x_out.exists():
                try:
                    temp_4x_out.unlink()
                except OSError:
                    pass

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
            "gpu_id": gpu_id,
            "file_size_bytes": out_size,
            "file_size_str": format_bytes(out_size),
            "processing_seconds": duration,
        }

    def list_models(self) -> List[Dict[str, Union[str, int]]]:
        """Returns all supported models with descriptions."""
        return [
            {"model_id": k, "scale": v["scale"], "type": v["type"], "description": v["description"]}
            for k, v in AVAILABLE_MODELS.items()
        ]
