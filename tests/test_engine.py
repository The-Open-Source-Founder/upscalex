"""
Unit and integration tests for RealESRGAN engine.
"""

import tempfile
from pathlib import Path
import pytest
from PIL import Image

from realesrgan_upscaler.engine import RealESRGANEngine, AVAILABLE_MODELS
from realesrgan_upscaler.utils import format_bytes, format_megapixels

@pytest.fixture
def sample_image():
    """Generates a temporary test image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = Path(f.name)
    
    # Create a 64x64 test image with colorful gradient
    img = Image.new("RGB", (64, 64), color=(120, 40, 200))
    img.save(img_path)
    yield img_path

    if img_path.exists():
        try:
            img_path.unlink()
        except OSError:
            pass

def test_format_helpers():
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1048576) == "1.00 MB"
    assert format_megapixels(1000, 1000) == "1.00 MP"
    assert format_megapixels(4024, 6252) == "25.16 MP"

def test_calculate_target_dimensions():
    engine = RealESRGANEngine(auto_download=False)
    
    # 16K (4x)
    w, h, desc = engine.calculate_target_dimensions(4024, 6252, "16k")
    assert w == 16096
    assert h == 25008

    # 8K (2x)
    w, h, desc = engine.calculate_target_dimensions(4024, 6252, "8k")
    assert w == 8048
    assert h == 12504

    # Custom
    w, h, desc = engine.calculate_target_dimensions(100, 200, "1000x2000")
    assert w == 1000
    assert h == 2000

def test_get_image_metadata(sample_image):
    engine = RealESRGANEngine(auto_download=False)
    meta = engine.get_image_metadata(sample_image)

    assert meta["width"] == 64
    assert meta["height"] == 64
    assert meta["aspect_ratio"] == 1.0
    assert meta["mode"] == "RGB"
    assert "print_size_300dpi_inches" in meta

def test_list_models():
    engine = RealESRGANEngine(auto_download=False)
    models = engine.list_models()
    assert len(models) == len(AVAILABLE_MODELS)
    assert any(m["model_id"] == "realesrgan-x4plus" for m in models)

def test_live_upscale(sample_image):
    """Integration test: runs actual 4x and supersampled 8k upscale."""
    engine = RealESRGANEngine(auto_download=True)
    out_dir = sample_image.parent / "test_out"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "sample_upscaled_4x.png"

    try:
        result = engine.upscale(
            input_path=sample_image,
            output_path=out_file,
            target="4x",
            model="realesrgan-x4plus",
            tile_size=64,
            gpu_id=1,
        )

        assert result["success"] is True
        assert out_file.exists()
        
        # Verify output dimensions (64x64 -> 256x256)
        with Image.open(out_file) as img:
            assert img.size == (256, 256)

    finally:
        if out_file.exists():
            out_file.unlink()
        if out_dir.exists():
            try:
                out_dir.rmdir()
            except OSError:
                pass
