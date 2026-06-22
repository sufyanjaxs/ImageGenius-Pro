# ImageGenius Pro ✦

**Advanced AI Image Generator & Professional Editing Suite**

Generate stunning images from text prompts, create procedural art, and edit with a full suite of professional tools — all in your browser.

## ✨ Features

### 🤖 AI Text-to-Image
- Generate from text prompts using Hugging Face models (FLUX, SDXL, SD 3.5)
- Custom negative prompts, resolution control
- Free tier available at huggingface.co

### 🎨 Procedural Generation
- Mandelbrot & Julia Fractals
- Perlin Noise, Plasma Fractals
- Gradients, Geometric Patterns
- Spirographs, Voronoi Diagrams
- Galaxy Generator, Wave Patterns
- Abstract Art Generator

### 🔧 Professional Editing Suite
- **Adjustments**: Brightness, Contrast, Saturation, Gamma, Exposure, Vibrance, Temperature, Hue, Highlights, Shadows
- **Filters**: Gaussian blur, sharpen, edge detect, emboss, sepia, grayscale, invert, posterize, pixelate, mosaic, oil paint, pencil sketch, neon, cartoon, thermal, vignette, noise, equalize + more
- **Transforms**: Resize, rotate, flip, crop
- **Effects**: Vignette, glow, kaleidoscope, wave distort, buldge, ripple, dream
- **Gradient Maps**: Multiple presets + custom
- **Channel Mixer**: RGB channel swapping/boosting
- **Drawing**: Text overlay with rotation/stroke, shapes (rect, ellipse, circle, line, arrow, polygon, star)
- **Layers & Blending**: 12 blend modes with opacity control

### 📁 File Support
- Upload images (drag & drop)
- Download as PNG or JPEG
- Full undo/redo history

## 🚀 Live Demo

https://sufyanjaxs.github.io/ImageGenius-Pro/

## 🔧 Usage

### AI Generation (requires API token)
1. Get a free token at https://huggingface.co/settings/tokens
2. Enter it in the AI tab
3. Type your prompt and click "Generate with AI"

### Procedural Generation
1. Switch to the "Generate" tab
2. Choose a generator type
3. Adjust parameters
4. Click "Generate"

### Editing
1. Load or generate an image
2. Use the various tabs (Adjust, Filters, Transform, Effects, Draw, Layers)
3. Undo/redo with Ctrl+Z / Ctrl+Shift+Z

## 🖥️ Local Development

```bash
# Backend (optional - for extended features)
pip install -r requirements.txt
python app.py

# Frontend (static, can be opened directly)
# Just open index.html in a browser
```

## 📦 Deployment

The main `index.html` is a fully self-contained static page deployable to GitHub Pages, Netlify, Vercel, or any static host.
