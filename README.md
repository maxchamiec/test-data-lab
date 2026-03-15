# Test Data Lab

A project for experimenting with testing and generating test data.

## Image generator

The script produces images in multiple formats with given dimensions (pixels and/or file size).

### Setup (local env in project folder only)

All dependencies are installed only inside the project folder (`.venv`). Nothing is installed system-wide.

**Windows (PowerShell, project-only, no system install):**

In the project folder run:

```powershell
cd test-data-lab
.\setup.ps1
```

If no system Python is found, the script downloads the official Windows embeddable Python into `.python\` (inside the project), then creates `.venv` and installs all dependencies there. Nothing is installed system-wide. If you already have Python on PATH, it will use that to create `.venv` and install only into the project.

Then start the app and open Chrome:

```powershell
.\run_app.ps1
```

**macOS / Linux:**

```bash
cd test-data-lab
python3 -m venv .venv
source .venv/bin/activate   # Windows Git Bash: .venv/Scripts/activate
pip install -r requirements.txt
```

**Web UI (local):**

```bash
python app.py
# Open http://127.0.0.1:5001 in your browser (5000 is often used by macOS AirPlay)
```

In the UI you can pick formats, dimensions, optional target file size, output subfolder, and filename prefix; then download the generated files.

**CLI:** run the script (with venv activated, or use `.venv/bin/python` without activating):

```bash
# Basic: one 800x600 PNG file
python generate_images.py --format png --width 800 --height 600

# Multiple formats
python generate_images.py --formats png jpeg webp --width 640 --height 480

# Target file size in bytes (for compressed formats)
python generate_images.py --format jpeg --width 800 --height 600 --target-size 50000

# Size in kilobytes
python generate_images.py --format png --target-size 100kb

# Output to a specific directory
python generate_images.py --formats png jpeg --width 200 --height 200 -o ./my_images

# Convert existing image to other formats
python generate_images.py -i photo.jpg --formats png webp pdf -o ./converted
```

### Options

| Option | Description |
|--------|-------------|
| `--format` / `-f` | Single format (e.g. png, jpeg, tiff, ico, pdf, heic) |
| `--formats` | Multiple formats (space-separated) |
| `--width` / `-W` | Width in pixels |
| `--height` / `-H` | Height in pixels |
| `--target-size` | Target file size (number = bytes, or 100kb, 2mb, 5gb) |
| `--output` / `-o` | Output directory (default `./output`) |
| `--prefix` | Filename prefix |

### Supported formats

| Key | Extension | Notes |
|-----|-----------|--------|
| png, jpeg, jpg, gif, webp, bmp | .png, .jpg, .gif, .webp, .bmp | Core formats; PNG/JPEG/WebP support `--target-size` |
| tiff, tif | .tiff, .tif | TIFF |
| ico | .ico | Windows icon (multiple sizes embedded) |
| pdf | .pdf | Single-page PDF (image as page) |
| heic, heif | .heic, .heif | Requires `pip install pillow-heif` |
| avif, dib, icns, pcx, ppm, tga, xbm, jp2, j2k | various | AVIF, DIB, macOS ICNS, PCX, PPM, TGA, XBM, JPEG 2000 |

For accurate file size, **JPEG** works best (quality is tuned automatically). PNG and WebP also support target size, but accuracy may be lower.

### Dependencies (all installed via `pip install -r requirements.txt`)

| Package | Purpose |
|---------|---------|
| **Pillow** | Image I/O and generation (PNG, JPEG, TIFF, WebP, GIF, BMP, ICO, PDF, AVIF, etc.). Pre-built wheels include libjpeg, zlib, libtiff, libwebp, openjpeg, libavif where available. |
| **pillow-heif** | HEIC/HEIF read and write. |
| **defusedxml** | Safe XMP metadata handling when Pillow reads images. |
| **olefile** | Pillow can read FPX and MIC formats. |
