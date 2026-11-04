"""
Tests for CLI commands including diagnostics and recommendation engine.
"""

from click.testing import CliRunner
from PIL import Image
import tempfile
from pathlib import Path

from upscalex.cli import main

def test_cli_models():
    runner = CliRunner()
    result = runner.invoke(main, ["models"], env={"COLUMNS": "160"})
    assert result.exit_code == 0
    assert "Installed" in result.output
    assert "4x-ultrasharp" in result.output

def test_cli_doctor():
    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "Operating System" in result.output
    assert "CPU Logical Cores" in result.output

def test_cli_recommend():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        p = Path(f.name)
    try:
        img = Image.new("RGB", (300, 300), color="green")
        img.save(p)

        result = runner.invoke(main, ["recommend", str(p)])
        assert result.exit_code == 0
        assert "Recommended Model" in result.output
        assert "Ready-to-Run Command" in result.output
    finally:
        if p.exists():
            p.unlink()

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
    assert "doctor" in result.output
    assert "models" in result.output
    assert "recommend" in result.output
    assert "download-model" in result.output
