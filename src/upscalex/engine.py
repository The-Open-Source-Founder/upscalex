"""
Core UpscaleX execution engine, resolution planner, cross-platform hardware resolver,
model catalog, and dynamic recommendation system.
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
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageFilter, ImageStat

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

# Comprehensive catalog of pre-packaged and downloadable open-weight models
MODEL_CATALOG = {
    "realesrgan-x4plus": {
        "name": "RealESRGAN X4plus",
        "scale": 4,
        "type": "Photos / Fine Art",
        "vram_tier": "Medium (4GB VRAM)",
        "min_vram_gb": 4,
        "files": ["realesrgan-x4plus.bin", "realesrgan-x4plus.param"],
        "download_url": None,
        "description": "Default flagship model for real-world photos, fine art, architectural renders, and poster prints.",
    },
    "realesrgan-x4plus-anime": {
        "name": "RealESRGAN Anime",
        "scale": 4,
        "type": "Anime / 2D Illustration",
        "vram_tier": "Medium (4GB VRAM)",
        "min_vram_gb": 4,
        "files": ["realesrgan-x4plus-anime.bin", "realesrgan-x4plus-anime.param"],
        "download_url": None,
        "description": "Optimized for 2D illustrations, anime art, vectors, and digital painting with crisp edge lines.",
    },
    "realesr-animevideov3-x4": {
        "name": "RealESRGAN Fast Video 4x",
        "scale": 4,
        "type": "Fast / Low VRAM",
        "vram_tier": "Low (1GB-2GB VRAM / CPU)",
        "min_vram_gb": 1,
        "files": ["realesr-animevideov3-x4.bin", "realesr-animevideov3-x4.param"],
        "download_url": None,
        "description": "Lightweight 4x feed-forward model designed for rapid processing and low VRAM GPUs.",
    },
    "realesr-animevideov3-x2": {
        "scale": 2,
        "name": "RealESRGAN Fast Video 2x",
        "type": "Fast / Low VRAM",
        "vram_tier": "Low (1GB-2GB VRAM / CPU)",
        "min_vram_gb": 1,
        "files": ["realesr-animevideov3-x2.bin", "realesr-animevideov3-x2.param"],
        "download_url": None,
        "description": "Fast 2x upscale model for video frames, small assets, and lightweight turnaround.",
    },
    "realesr-animevideov3-x3": {
        "scale": 3,
        "name": "RealESRGAN Fast Video 3x",
        "type": "Fast / Low VRAM",
        "vram_tier": "Low (1GB-2GB VRAM / CPU)",
        "min_vram_gb": 1,
        "files": ["realesr-animevideov3-x3.bin", "realesr-animevideov3-x3.param"],
        "download_url": None,
        "description": "Fast 3x upscale model for video frames, web assets, and rapid turnaround.",
    },
    "realesr-general-x4v3": {
        "name": "RealESRGAN General v3 Compact",
        "scale": 4,
        "type": "General / Compact",
        "vram_tier": "Low (2GB VRAM)",
        "min_vram_gb": 2,
        "files": ["realesr-general-x4v3.pth"],
        "download_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
        "description": "Official compact general 4x model optimized for quick inference and lower memory consumption.",
    },
    "4x-ultrasharp": {
        "name": "4x UltraSharp (Community Edition)",
        "scale": 4,
        "type": "Portraits / Ultra-Detail",
        "vram_tier": "Medium-High (4GB-6GB VRAM)",
        "min_vram_gb": 4,
        "files": ["4x-UltraSharp.pth"],
        "download_url": "https://huggingface.co/lokcx/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth",
        "description": "Community champion ESRGAN model famous for razor-sharp portraits, fabric, skin, and micro-textures.",
    },
    "4x-nmkd-superscale": {
        "name": "4x NMKD Superscale",
        "scale": 4,
        "type": "Clean Photorealistic",
        "vram_tier": "Medium-High (4GB-6GB VRAM)",
        "min_vram_gb": 4,
        "files": ["4x_NMKD-Superscale-SP_178000_G.pth"],
        "download_url": "https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x_NMKD-Superscale-SP_178000_G.pth",
        "description": "Trained on clean photographs; preserves fine hair, clothing threads, and foliage without artifacts.",
    },
    "realesrgan-anime-6b": {
        "name": "RealESRGAN Anime 6-Block Lightweight",
        "scale": 4,
        "type": "Anime / Fast",
        "vram_tier": "Low (1GB-2GB VRAM / CPU)",
        "min_vram_gb": 1,
        "files": ["RealESRGAN_x4plus_anime_6B.pth"],
        "download_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        "description": "Lightweight 6-block architecture for fast anime inference with low compute overhead.",
    },
}

# Legacy alias dictionary for backward compatibility
AVAILABLE_MODELS = {k: {"scale": v["scale"], "type": v["type"], "description": v["description"]} for k, v in MODEL_CATALOG.items()}

class RealESRGANEngine:
    """
    Manages RealESRGAN binary execution, cross-platform hardware resolution (Vulkan GPU vs CPU),
    dynamic model downloading, model recommendation, and resolution supersampling.
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
        if custom_path:
            p = Path(custom_path)
            if p.is_file() and os.access(p, os.X_OK):
                return p.resolve()
            if p.is_dir():
                cand = p / get_binary_name()
                if cand.exists():
                    return cand.resolve()

        env_val = os.environ.get("REALESRGAN_PATH")
        if env_val:
            p = Path(env_val)
            if p.is_file():
                return p.resolve()

        common_candidates = [
            Path(r"C:\Companies\printing_businesses\tools\realesrgan") / get_binary_name(),
            get_default_cache_dir() / get_binary_name(),
            Path.cwd() / "tools" / "realesrgan" / get_binary_name(),
            Path.cwd() / get_binary_name(),
        ]
        for cand in common_candidates:
            if cand.exists():
                return cand.resolve()

        which_path = shutil.which(get_binary_name()) or shutil.which("realesrgan-ncnn-vulkan")
        if which_path:
            return Path(which_path).resolve()

        if auto_download:
            try:
                return download_and_extract_engine().resolve()
            except Exception:
                pass

        return get_default_cache_dir() / get_binary_name()

    def _resolve_models_dir(self, custom_models_dir: Optional[Union[str, Path]]) -> Path:
        """Locates the models directory."""
        if custom_models_dir:
            p = Path(custom_models_dir)
            if p.is_dir():
                return p.resolve()

        adjacent = self.binary_path.parent / "models"
        if adjacent.is_dir():
            return adjacent.resolve()

        cached = get_default_cache_dir() / "models"
        if cached.is_dir():
            return cached.resolve()

        return adjacent

    def is_model_installed(self, model_id: str) -> bool:
        """Checks if all required model weight files exist locally."""
        if model_id not in MODEL_CATALOG:
            return False
        meta = MODEL_CATALOG[model_id]
        return all((self.models_dir / f).exists() for f in meta["files"])

    def download_model(self, model_id: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """
        Downloads open-weight model files from upstream mirrors directly into the models directory.
        """
        if model_id not in MODEL_CATALOG:
            valid = ", ".join(MODEL_CATALOG.keys())
            raise ValueError(f"Unknown model '{model_id}'. Catalog models: {valid}")

        meta = MODEL_CATALOG[model_id]
        if self.is_model_installed(model_id):
            return {
                "success": True,
                "model_id": model_id,
                "name": meta["name"],
                "status": "already_installed",
                "message": f"Model '{meta['name']}' is already installed.",
                "path": str(self.models_dir),
            }

        url = meta.get("download_url")
        if not url:
            raise RuntimeError(
                f"Model '{model_id}' is part of the core binary bundle. Run 'upscalex download-engine' to fetch it."
            )

        self.models_dir.mkdir(parents=True, exist_ok=True)
        dest_filename = meta["files"][0]
        dest_path = self.models_dir / dest_filename

        try:
            def reporthook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    progress_callback(block_num * block_size, total_size)

            urllib.request.urlretrieve(url, str(dest_path), reporthook=reporthook)

            return {
                "success": True,
                "model_id": model_id,
                "name": meta["name"],
                "status": "downloaded",
                "message": f"Model '{meta['name']}' successfully downloaded.",
                "file": dest_filename,
                "path": str(dest_path),
                "size_bytes": dest_path.stat().st_size,
                "size_str": format_bytes(dest_path.stat().st_size),
            }
        except Exception as e:
            if dest_path.exists():
                try:
                    dest_path.unlink()
                except OSError:
                    pass
            raise RuntimeError(f"Failed to download model '{model_id}' from {url}: {e}")

    def recommend_model(self, image_path: Union[str, Path], priority: str = "balanced") -> Dict[str, Any]:
        """
        Inspects host hardware specifications (GPU VRAM, CPU cores) and image characteristics
        (color variance, entropy, resolution) to recommend the optimal upscaling model and settings.
        """
        in_p = Path(image_path).resolve()
        if not in_p.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        diag = self.get_system_diagnostics()
        meta = self.get_image_metadata(in_p)

        # Image content heuristic: analyze color variance & flat region ratio
        with Image.open(in_p) as img:
            thumb = img.convert("RGB").resize((128, 128))
            stat = ImageStat.Stat(thumb)
            avg_stddev = sum(stat.stddev) / 3.0
            unique_colors = len(thumb.getcolors(maxcolors=16384) or [])

        # Classification heuristic: low variance / restricted palette -> 2D/Anime/Vector; high variance -> Photo
        is_illustration = (unique_colors < 6000 and avg_stddev < 60.0) or (unique_colors < 3500)
        image_class = "2D Illustration / Vector Art / Anime" if is_illustration else "Photographic / Continuous Tone / Fine Art"

        # Hardware evaluation
        has_gpu = diag["has_vulkan_gpu"]
        discrete_gpus = [g for g in diag.get("detected_gpus", []) if g.get("is_discrete")]
        is_discrete = len(discrete_gpus) > 0
        gpu_name = discrete_gpus[0]["name"] if is_discrete else (diag.get("detected_gpus", [{}])[0].get("name") if has_gpu else "CPU")

        # Determine target resolution preset
        orig_mp = meta["megapixels"]
        if orig_mp >= 20.0:
            rec_target = "16k"
            target_reason = "Source image is >=20 MP. Native 16K (4x) upscale is ideal for large-format exhibition master prints."
        elif orig_mp >= 5.0:
            rec_target = "8k"
            target_reason = "Source image is 5-20 MP. 8K supersampling (4x + Lanczos) delivers maximum edge clarity with zero noise."
        else:
            rec_target = "4k"
            target_reason = "Source image is low-resolution (<5 MP). 4K target provides clean restoration without over-magnifying artifacts."

        # Select model and settings based on hardware + content
        if not has_gpu:
            rec_model = "realesr-animevideov3-x4" if is_illustration else "realesrgan-x4plus"
            rec_tile = 128
            hw_tier = "CPU Multi-Threaded"
            rec_reasoning = f"No discrete GPU detected. Using {rec_model} with 128px tiling for CPU-safe execution."
        elif not is_discrete:
            # Integrated GPU (Intel UHD / Iris)
            rec_model = "realesr-animevideov3-x4" if is_illustration else "realesrgan-x4plus"
            rec_tile = 128
            hw_tier = "Integrated GPU (Shared System RAM)"
            rec_reasoning = f"Integrated GPU detected ({gpu_name}). 128px tiling prevents system memory pressure and driver timeouts."
        else:
            # Dedicated GPU (RTX / Radeon)
            rec_tile = 256
            hw_tier = f"Dedicated GPU ({gpu_name})"
            if is_illustration:
                rec_model = "realesrgan-x4plus-anime"
                rec_reasoning = f"Detected {image_class} on {gpu_name}. 'realesrgan-x4plus-anime' provides clean contour preservation and flat color smoothing."
            else:
                rec_model = "realesrgan-x4plus"
                rec_reasoning = f"Detected {image_class} on {gpu_name}. 'realesrgan-x4plus' with 256px tiling delivers pristine textural and fine-art fidelity."

        cmd_sample = f'upscalex upscale "{in_p.name}" --target {rec_target} --model {rec_model} --tile-size {rec_tile}'

        return {
            "image_path": str(in_p),
            "file_name": in_p.name,
            "detected_content_type": image_class,
            "hardware_tier": hw_tier,
            "recommended_model": rec_model,
            "recommended_target": rec_target,
            "recommended_tile_size": rec_tile,
            "recommended_gpu_id": "auto",
            "target_resolution_reasoning": target_reason,
            "model_selection_reasoning": rec_reasoning,
            "ready_command": cmd_sample,
            "is_model_installed": self.is_model_installed(rec_model),
        }

    def resolve_device(self, requested_gpu: Optional[Union[int, str]] = "auto") -> Tuple[str, Optional[int]]:
        """
        Determines execution device: 'vulkan' with device ID, or 'cpu'.
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
        """High-performance multi-threaded CPU fallback upscaler."""
        if progress_callback:
            progress_callback(10.0)

        with Image.open(in_p) as img:
            rgb_img = img.convert("RGB")
            if progress_callback:
                progress_callback(30.0)

            upscaled = rgb_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            if progress_callback:
                progress_callback(70.0)

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
        """
        in_p = Path(input_path).resolve()
        if not in_p.is_file():
            raise FileNotFoundError(f"Input image not found: {input_path}")

        if model not in MODEL_CATALOG:
            valid = ", ".join(MODEL_CATALOG.keys())
            raise ValueError(f"Invalid model '{model}'. Available models: {valid}")

        # Ensure model weights are available
        if not self.is_model_installed(model):
            # Auto download if downloadable
            if MODEL_CATALOG[model].get("download_url"):
                self.download_model(model)
            else:
                raise FileNotFoundError(f"Model weights for '{model}' not found in {self.models_dir}.")

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

    def list_models(self) -> List[Dict[str, Any]]:
        """Returns all catalog models with local installation status and specifications."""
        result = []
        for k, v in MODEL_CATALOG.items():
            result.append({
                "model_id": k,
                "name": v["name"],
                "scale": v["scale"],
                "type": v["type"],
                "vram_tier": v["vram_tier"],
                "installed": self.is_model_installed(k),
                "downloadable": bool(v.get("download_url")),
                "description": v["description"],
            })
        return result
