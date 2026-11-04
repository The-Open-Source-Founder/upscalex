"""
Tests for CLI commands.
"""

from click.testing import CliRunner
from PIL import Image
import tempfile
from pathlib import Path

from upscalex.cli import main

def test_cli_models():
    runner = CliRunner()
    result = runner.invoke(main, ["models"])
    assert result.exit_code == 0
    assert "realesrgan-x4plus" in result.output

def test_cli_info():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        p = Path(f.name)
    try:
        img = Image.new("RGB", (300, 300), color="blue")
        img.save(p)

        result = runner.invoke(main, ["info", str(p)])
        assert result.exit_code == 0
        assert "300 × 300" in result.output
        assert "Print Size" in result.output
    finally:
        if p.exists():
            p.unlink()

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "upscale" in result.output
    assert "serve" in result.output
    assert "models" in result.output
