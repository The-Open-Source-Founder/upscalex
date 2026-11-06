# UpscaleX: 6-Slide Instagram Carousel Content & Specification

**Format:** 1080 x 1350 px (4:5 Portrait)  
**Aesthetic:** Midnight royal blue gradient background matching the README banner, modest font hierarchy, mild glassmorphism surfaces, crisp 1px borders, zero emojis, zero em-dashes.  
**Canva Live Design:** [https://www.canva.com/d/P4GzcCNN8HWN1s7](https://www.canva.com/d/P4GzcCNN8HWN1s7)  

---

## Slide 1: Hook & One-Line Quickstart
* **Header:** `01 / 06` | `UpscaleX`
* **Main Headline:** `Upscale to 16K without crashing your GPU`
* **Subheader:** `Production-grade RealESRGAN super-resolution with native Vulkan acceleration and spatial 256px tiling.`
* **Quickstart Pill:** `pip install upscalex`

---

## Slide 2: Empirical Proof & Visual Receipt
* **Header:** `02 / 06` | `UpscaleX`
* **Main Headline:** `0.35 MP to 5.63 MP. 16x Pixel Density`
* **Tag:** `Empirical Benchmark`
* **Comparison Metrics:**
  - `Before: 0.35 MP` (480p Crop)
  - `After: 5.63 MP` (4x Inference)
  - `16x Pixel Density Reconstruction`

---

## Slide 3: Unified All-in-One Model Gateway
* **Header:** `03 / 06` | `UpscaleX`
* **Main Headline:** `Unified All-in-One Model Gateway`
* **Subheadline:** `One interface, specialized paths.`
* **Gateway Routing Channels:**
  - `RealESRGAN-x4plus`: Photorealistic texture reconstruction
  - `RealESR_General_x4v3`: Low-noise web compression artifact removal
  - `Anime 6B`: Vector and 2D illustration synthesis
  - `Lanczos-3`: Deep supersampling anti-aliasing

---

## Slide 4: System Architecture Primitives
* **Header:** `04 / 06` | `UpscaleX`
* **Main Headline:** `System Architecture`
* **Pillars:**
  - `01. Spatial 256px Sliding-Window Tiling`: Caps peak VRAM below 1.2GB, preventing CUDA OOM crashes.
  - `02. Native Vulkan GPU Compute`: Cross-platform hardware acceleration on Windows, Linux, and macOS with CPU fallback.
  - `03. Lanczos-3 SSAA`: Downscales 4x deep-learning inference to target 8K output to eliminate ringing.

---

## Slide 5: Autonomous AI Agent Integration
* **Header:** `05 / 06` | `UpscaleX`
* **Main Headline:** `AI Agent Integration`
* **Subheadline:** `Built for agent-native workflows.`
* **Protocol Details:**
  - Native FastMCP server via stdio JSON-RPC
  - Supported runtimes: Claude Desktop, Cursor, Antigravity
  - Unified tools: `upscale_image`, `recommend_model`, `calculate_print_dpi`

---

## Slide 6: Open Source & Closer
* **Header:** `06 / 06` | `UpscaleX`
* **Main Headline:** `Open Source, Ready to Run`
* **Terminal Commands:**
  - `pip install upscalex`
  - `upscalex doctor`
  - `upscalex upscale input.png --target 16k`
* **Repository:** `github.com/The-Open-Source-Founder/upscalex`
* **Closing Tagline:** `Scale images. Keep control.`
