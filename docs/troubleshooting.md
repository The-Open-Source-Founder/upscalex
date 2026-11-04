# UpscaleX Error Handling and Troubleshooting Reference

This document catalogs all known failure modes, error codes, and recovery procedures across the CLI, MCP server, and underlying compute runtimes.

---

## 1. File and Input Errors

### Error: `Input image not found` / `FileNotFoundError`
- **Cause**: The specified image path does not exist, was mistyped, or is a directory rather than a file.
- **Resolution**:
  - Provide an absolute path (e.g. `C:\images\photo.png` or `/home/user/images/photo.png`).
  - Verify file existence with `ls` or `dir`.
  - In MCP calls, ensure relative paths resolve relative to the current working workspace.

### Error: `File is not a valid decodeable image` / `UnidentifiedImageError`
- **Cause**: The input file is empty (0 bytes), corrupted, or is an unsupported format (e.g. PDF, raw text, HTML error page saved as `.png`).
- **Resolution**:
  - Run `upscalex info <path>` to test header readability.
  - Verify supported formats: PNG, JPG, JPEG, WEBP, BMP, TIFF.
  - Check file size to ensure complete download.

### Issue: Image Colors Appear Inverted or Corrupted (CMYK Print Files)
- **Cause**: Commercial print shops frequently receive CMYK JPEG/TIFF files. Many neural network runtimes only understand 3-channel sRGB or 4-channel RGBA.
- **Resolution**: UpscaleX features automated pre-flight sanitization. Any CMYK, Palette (`P`), or 1-bit monochrome image is automatically converted to clean 8-bit sRGB before passing to the inference engine.

### Issue: Mobile Phone Photos Upscale Upside Down or Rotated
- **Cause**: Smartphone cameras (iPhone, Android) store rotation orientation in EXIF tags (`Orientation=6`). Raw C++ runtimes often ignore EXIF and render the unrotated sensor orientation.
- **Resolution**: UpscaleX automatically applies `ImageOps.exif_transpose()` during pre-flight validation, ensuring all photos upscale in their correct viewing orientation.

---

## 2. Memory and Resolution Errors

### Error: `DecompressionBombError: Image size exceeds limit`
- **Cause**: Python Pillow by default blocks opening images larger than ~178 Megapixels to protect against zip bomb denial-of-service attacks. A 16K image (`16,096 × 25,008`) contains over 402 Megapixels.
- **Resolution**:
  - UpscaleX internally sets `Image.MAX_IMAGE_PIXELS = None` across all modules.
  - In custom scripts importing Pillow to view UpscaleX outputs, add:
    ```python
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    ```

### Error: GPU Out-Of-Memory (OOM) or Driver Timeout (TDR on Windows)
- **Cause**: The `--tile-size` is set too high for the available GPU VRAM (e.g. attempting `--tile-size 600` on a 4GB laptop GPU), or Windows Timeout Detection and Recovery (TDR) kills the GPU kernel after 2 seconds of continuous compute.
- **Resolution**:
  - Use `--tile-size 256` (safe for 4GB VRAM).
  - On integrated GPUs (Intel UHD / Iris), use `--tile-size 128`.
  - Alternatively, force multi-threaded CPU mode:
    ```bash
    upscalex upscale input.png --target 8k --gpu-id cpu
    ```

### Error: `Unknown target resolution` / Syntax Errors
- **Cause**: The `--target` argument was formatted incorrectly (e.g. `--target 1000` without height).
- **Supported Targets**:
  - Presets: `16k`, `8k`, `4k`, `4x`, `2x`, `3x`.
  - Custom Dimensions: `WIDTHxHEIGHT` (e.g. `--target 12000x8000`).

---

## 3. Hardware and Vulkan GPU Errors

### Error: `vkCreateInstance failed` or `No Vulkan device found`
- **Cause**: The system lacks Vulkan graphics drivers (e.g. a minimal headless Docker container, a remote Linux VM without GPU passthrough, or outdated GPU drivers).
- **Resolution**:
  - UpscaleX automatically detects this condition and transitions to multi-threaded CPU Lanczos super-resolution.
  - To force CPU execution explicitly:
    ```bash
    upscalex upscale input.png --gpu-id cpu
    ```
  - On Linux host machines, install Vulkan drivers:
    ```bash
    sudo apt-get install libvulkan1 vulkan-tools
    ```

### Error: `Invalid GPU ID` (e.g. `--gpu-id 5`)
- **Cause**: The requested GPU index does not exist on the host machine.
- **Resolution**:
  - Run `upscalex doctor` to enumerate all available compute devices and their indices:
    ```bash
    upscalex doctor
    ```
  - Leave `--gpu-id auto` to allow UpscaleX to select the optimal dedicated GPU automatically.

---

## 4. Platform-Specific Errors

### macOS: `Killed: 9` or Gatekeeper Security Popups
- **Cause**: macOS applies a quarantine extended attribute (`com.apple.quarantine`) to binaries downloaded over HTTP/HTTPS, preventing unsigned precompiled binaries from executing.
- **Resolution**:
  - UpscaleX's downloader automatically strips quarantine flags using `xattr -cr`.
  - If encountering issues with manual binaries:
    ```bash
    xattr -cr ~/.cache/realesrgan-upscaler/
    chmod +x ~/.cache/realesrgan-upscaler/realesrgan-ncnn-vulkan
    ```

### Linux: `libvulkan.so.1: cannot open shared object file`
- **Cause**: Missing dynamic Vulkan loader libraries on minimal Linux distributions.
- **Resolution**:
  ```bash
  # Ubuntu / Debian
  sudo apt install libvulkan1

  # Fedora / RHEL
  sudo dnf install vulkan-loader
  ```

### Windows: `vcomp140.dll was not found`
- **Cause**: Missing Microsoft Visual C++ 2015-2022 Redistributable.
- **Resolution**: Install the official x64 redistributable from Microsoft:
  `https://aka.ms/vs/17/release/vc_redist.x64.exe`
  (UpscaleX includes fallback `vcomp140.dll` in its engine distribution directory).

---

## 5. Model Catalog and Network Errors

### Error: `Model weights not found` / Download Interrupted
- **Cause**: Network disconnection or firewall blocking GitHub/HuggingFace CDNs during `download-model`.
- **Resolution**:
  - Ensure internet access to `github.com` and `huggingface.co`.
  - Re-run model download:
    ```bash
    upscalex download-model <model_id>
    ```
  - Incomplete temporary download files are automatically discarded to avoid corrupted weight files.

---

## 6. Model Context Protocol (MCP) Errors

### Issue: Claude Desktop or Cursor Fails to Parse MCP Server Output
- **Cause**: Non-JSON output written to `stdout` breaks the JSON-RPC framing protocol.
- **Resolution**:
  - UpscaleX routes all terminal progress indicators, status messages, and diagnostics exclusively to `stderr`.
  - Only valid JSON-RPC frames are transmitted over `stdout`.

### Issue: MCP Server Hangs or Timeouts
- **Cause**: A massive 16K upscale on a weak CPU or huge image can take several minutes, triggering client timeout thresholds.
- **Resolution**:
  - Use `recommend_model` first to inspect resolution viability.
  - On low-spec machines, recommend `8k` or `4k` presets before proceeding to full `16k` prints.

---

## 7. Diagnostic Checklist

When reporting issues or troubleshooting unexpected behavior, run the following diagnostic commands:

```bash
# 1. Inspect hardware environment, detected GPUs, and CPU threads
upscalex doctor

# 2. Inspect model catalog and installation status
upscalex models

# 3. Test image file readability and print sizing
upscalex info "/path/to/image.png"

# 4. Run test suite to verify internal engine integrity
uv run pytest -v
```
