# UpscaleX Architecture and Technical Specification

This document provides a technical breakdown of the UpscaleX engine architecture, inference pipeline, memory bounds, and supersampling mathematical foundation.

---

## 1. High-Level System Architecture

UpscaleX bridges native high-performance C++ Vulkan neural network runtimes with modern Python AI agent ecosystems through standard Model Context Protocol (MCP) and command-line interfaces.

```
+-------------------------------------------------------------------------+
|                              Entry Points                               |
|        CLI (click + rich)             |       FastMCP Server (JSON-RPC) |
+---------------------------------------+---------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                           Core Engine Layer                             |
|                           (RealESRGANEngine)                            |
|                                                                         |
|  - Spatial Resolution Planner         - Binary / Model Environment Check|
|  - Tile Dimension Allocator           - Process Lifecycle Manager       |
+-------------------------------------------------------------------------+
                    |                                   |
                    v                                   v
+---------------------------------------+   +-----------------------------+
|        Vulkan Compute Pipeline        |   |    Post-Processing Layer    |
|       (realesrgan-ncnn-vulkan)        |   |    (Lanczos Supersampling)  |
|                                       |   |                             |
|  - NCNN Neural Inference              |   |  - Pillow Fast C Resampling |
|  - Hardware Texture Tiling            |   |  - SSAA Anti-Aliasing Pass  |
|  - Cross-GPU Vulkan Device Index      |   |  - Uncompressed File Writer |
+---------------------------------------+   +-----------------------------+
```

---

## 2. RealESRGAN Deep-Learning Foundation

RealESRGAN extends the classical ESRGAN (Enhanced Super-Resolution Generative Adversarial Networks) architecture by using a high-order degradation modeling process during training.

### Residual-in-Residual Dense Block (RRDB)
The core backbone consists of RRDB blocks that concatenate feature maps from preceding convolutional layers, preserving multi-scale spatial frequencies and textural fidelity.

### High-Order Degradation Modeling
Unlike conventional bicubic upscalers, RealESRGAN's generator is trained against composite real-world degradation pipelines:
$$\text{Degradation}(x) = (x \ast k_{\sigma} \downarrow_{s} + n) \ast \text{JPEG}_{q}$$
where $k_{\sigma}$ represents anisotropic Gaussian blur kernels, $\downarrow_{s}$ is spatial downsampling, $n$ represents additive Gaussian or Poisson camera sensor noise, and $\text{JPEG}_{q}$ simulates lossy compression artifacts.

This enables the model to reconstruct fine architectural details, typographic edges, and cloth textures rather than amplifying compression noise.

---

## 3. Spatial Tiling and VRAM Bounds

A major challenge when upscaling images to 16K (`16,096 × 25,008` pixels) is memory allocation. A single uncompressed RGB 16K bitmap occupies over 1.2 GB of raw RAM, and feeding a full 25 Megapixel frame into deep convolutional layers would require over 64 GB of contiguous GPU VRAM.

### Overlapping Tile Decomposition

UpscaleX utilizes overlapping spatial tile decomposition to maintain fixed memory footprints:

1. The input image of dimensions $W \times H$ is partitioned into tiles of size $T \times T$ (configured via `--tile-size`, default 256 px).
2. Each tile is padded with an overlap boundary (typically 10 to 16 pixels) to avoid boundary seam artifacts caused by convolution padding.
3. The tile is copied into GPU device memory via Vulkan textures.
4. Inference runs on the tile, outputting a $4T \times 4T$ block.
5. Padded overlap boundaries are blended, and the output tile is written into the destination raster.

### Theoretical VRAM Requirement Formula

$$\text{VRAM}_{\text{peak}} \approx c \times T^{2} \times D_{\text{layers}} \times \text{sizeof}(\text{fp16})$$

Where:
- $T$: Tile dimension (e.g. 256 or 400).
- $D_{\text{layers}}$: Activation depth of intermediate feature maps.
- At $T = 256$, peak VRAM usage remains strictly under **1.2 GB**, allowing execution on 4 GB laptop GPUs (such as NVIDIA GeForce RTX 3050 Laptop) with zero stability degradation.

---

## 4. Lanczos Supersampling Mathematical Foundation

To produce pristine 8K images, UpscaleX avoids running non-native 2× models directly. Instead, it utilizes **4× RealESRGAN inference followed by Lanczos-3 downsampling**.

This pipeline functions as high-order **Supersampling Anti-Aliasing (SSAA)**:
1. High-frequency details and edge reconstructions are synthesized at 16K resolution (400+ Megapixels).
2. Downsampling to 8K averages pixel neighborhoods through a 3-lobed Lanczos sinc kernel:

$$L(x) = \begin{cases} \text{sinc}(x) \, \text{sinc}(x / a) & \text{if } -a < x < a \\ 0 & \text{otherwise} \end{cases}$$

where $a = 3$ is the filter radius and $\text{sinc}(x) = \frac{\sin(\pi x)}{\pi x}$.

This suppresses high-frequency aliasing, ringing, and pixel crawling while retaining razor-sharp line definition.

---

## 5. Print Sizing and DPI Reference

In professional digital printing, physical print size is governed by pixel density:

$$\text{Print Dimension (Inches)} = \frac{\text{Pixel Dimension}}{\text{DPI}}$$

### Standard Print Scale Matrix

| Image Scale | Pixel Dimensions | Megapixels | Max Print Size at 300 DPI | Max Print Size at 150 DPI |
| :--- | :--- | :--- | :--- | :--- |
| **Original 4K** | `4,024 × 6,252` | 25.16 MP | 13.4 × 20.8 inches (A3 / Small Poster) | 26.8 × 41.7 inches |
| **UpscaleX 8K** | `8,048 × 12,504` | 100.63 MP | 26.8 × 41.7 inches (A1 / Large Poster) | 53.6 × 83.4 inches |
| **UpscaleX 16K** | `16,096 × 25,008` | 402.53 MP | **53.6 × 83.4 inches** (Billboard / Exhibition) | **107.2 × 166.8 inches** |
