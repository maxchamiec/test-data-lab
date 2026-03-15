#!/usr/bin/env python3
"""
Test image generator for multiple formats.
Produces files in the requested format and (when possible) target file size in bytes.
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from PIL import Image  # pylint: disable=import-error

# Optional HEIF/HEIC support via pillow-heif
try:
    from pillow_heif import register_heif_opener  # pylint: disable=import-error
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False


# File extension and PIL format name per format key.
# HEIC/HEIF require: pip install pillow-heif
FORMATS = {
    # Core (Pillow)
    "png": (".png", "PNG"),
    "jpeg": (".jpg", "JPEG"),
    "jpg": (".jpg", "JPEG"),
    "jfif": (".jfif", "JPEG"),
    "gif": (".gif", "GIF"),
    "webp": (".webp", "WEBP"),
    "bmp": (".bmp", "BMP"),
    "tiff": (".tiff", "TIFF"),
    "tif": (".tif", "TIFF"),
    "ico": (".ico", "ICO"),
    "pdf": (".pdf", "PDF"),
    # Optional: requires pillow-heif
    "heic": (".heic", "HEIF"),
    "heif": (".heif", "HEIF"),
    # Additional image formats (Pillow)
    "avif": (".avif", "AVIF"),
    "dib": (".dib", "DIB"),
    "icns": (".icns", "ICNS"),
    "pcx": (".pcx", "PCX"),
    "ppm": (".ppm", "PPM"),
    "tga": (".tga", "TGA"),
    "xbm": (".xbm", "XBM"),
    "jp2": (".jp2", "JPEG2000"),
    "j2k": (".jp2", "JPEG2000"),
}


def parse_size(value: str) -> int:
    """Parse size: number in bytes or with kb/mb suffix."""
    value = value.strip().lower()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(kb|mb|bytes?)?$", value)
    if not m:
        raise ValueError(f"Invalid size: {value!r}. Examples: 1024, 100kb, 2mb")
    num = float(m.group(1))
    unit = (m.group(2) or "bytes").rstrip("s")
    if unit == "byte" or unit == "bytes":
        return int(num)
    if unit == "kb":
        return int(num * 1024)
    if unit == "mb":
        return int(num * 1024 * 1024)
    return int(num)


def make_image(width: int, height: int, content: str = "gradient") -> Image.Image:
    """
    Create an image of the given dimensions.
    content: 'solid' for flat color, 'gradient' for gradient (affects compressed size more).
    """
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    if content == "solid":
        for y in range(height):
            for x in range(width):
                pixels[x, y] = (x % 256, y % 256, 128)
    else:
        for y in range(height):
            for x in range(width):
                r = int(255 * x / max(width, 1)) % 256
                g = int(255 * y / max(height, 1)) % 256
                b = (x + y) % 256
                pixels[x, y] = (r, g, b)
    return img


def save_png(img: Image.Image, path: Path, compress_level: int = 6) -> int:
    """Save as PNG and return file size in bytes."""
    img.save(path, "PNG", compress_level=compress_level)
    return path.stat().st_size


def save_jpeg(img: Image.Image, path: Path, quality: int = 85) -> int:
    """Save as JPEG and return file size in bytes."""
    img.save(path, "JPEG", quality=quality, optimize=True)
    return path.stat().st_size


def save_webp(img: Image.Image, path: Path, quality: int = 80) -> int:
    """Save as WebP and return file size in bytes."""
    img.save(path, "WEBP", quality=quality)
    return path.stat().st_size


def save_gif(img: Image.Image, path: Path) -> int:
    """Save as GIF (single frame)."""
    img.save(path, "GIF")
    return path.stat().st_size


def save_bmp(img: Image.Image, path: Path) -> int:
    """Save as BMP."""
    img.save(path, "BMP")
    return path.stat().st_size


def png_to_target_size(
    img: Image.Image, path: Path, target_bytes: int, width: int, height: int
) -> int:
    """
    Find PNG compression level to get close to target_bytes.
    If that fails, scale the image down and try again.
    """
    for level in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]:
        save_png(img, path, compress_level=level)
        size = path.stat().st_size
        if size <= target_bytes * 1.1:
            return size
    # Still too large at minimum compression — scale down
    scale = (target_bytes / (path.stat().st_size or 1)) ** 0.5
    scale = max(0.1, min(1.0, scale))
    new_w = max(1, int(width * scale))
    new_h = max(1, int(height * scale))
    small = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    for level in [9, 6, 3, 0]:
        save_png(small, path, compress_level=level)
        if path.stat().st_size <= target_bytes * 1.2:
            return path.stat().st_size
    return path.stat().st_size


def jpeg_to_target_size(
    img: Image.Image, path: Path, target_bytes: int
) -> int:
    """Binary search on quality to get close to target_bytes."""
    lo, hi = 1, 100
    best_size = 0
    for _ in range(12):
        q = (lo + hi) // 2
        size = save_jpeg(img, path, quality=q)
        best_size = size
        if abs(size - target_bytes) < 500:
            return size
        if size > target_bytes:
            hi = q - 1
        else:
            lo = q + 1
        if lo > hi:
            break
    return best_size


def webp_to_target_size(
    img: Image.Image, path: Path, target_bytes: int
) -> int:
    """Binary search on quality for WebP."""
    lo, hi = 1, 100
    best_size = 0
    for _ in range(12):
        q = (lo + hi) // 2
        size = save_webp(img, path, quality=q)
        best_size = size
        if abs(size - target_bytes) < 500:
            return size
        if size > target_bytes:
            hi = q - 1
        else:
            lo = q + 1
        if lo > hi:
            break
    return best_size


def load_image(path: Path) -> Image.Image:
    """Load image from file and convert to RGB for broad format support."""
    img = Image.open(path).convert("RGB")
    return img


def convert_one(
    img: Image.Image,
    fmt: str,
    output_dir: Path,
    prefix: str,
    target_size: Optional[int],
) -> tuple:
    """
    Save the given image in one format; return (path, size_bytes).
    """
    width, height = img.size
    return _save_one(img, fmt, output_dir, prefix, target_size, width, height)


def _save_one(
    img: Image.Image,
    fmt: str,
    output_dir: Path,
    prefix: str,
    target_size: Optional[int],
    width: int,
    height: int,
) -> tuple:
    """Common save logic for one format (used by generate_one and convert_one)."""
    fmt_lower = fmt.lower()
    if fmt_lower not in FORMATS:
        raise ValueError(f"Format {fmt!r} is not supported. Available: {list(FORMATS.keys())}")
    ext, pil_fmt = FORMATS[fmt_lower]
    if pil_fmt == "HEIF" and not HEIF_AVAILABLE:
        raise ValueError(
            "HEIC/HEIF format requires pillow-heif. Install with: pip install pillow-heif"
        )
    name = f"{prefix}{fmt_lower}{ext}"
    path = output_dir / name

    if target_size is not None and pil_fmt in ("PNG", "JPEG", "WEBP"):
        if pil_fmt == "PNG":
            size = png_to_target_size(img, path, target_size, width, height)
        elif pil_fmt == "JPEG":
            size = jpeg_to_target_size(img, path, target_size)
        else:
            size = webp_to_target_size(img, path, target_size)
    else:
        if pil_fmt == "PNG":
            size = save_png(img, path)
        elif pil_fmt == "JPEG":
            size = save_jpeg(img, path)
        elif pil_fmt == "WEBP":
            size = save_webp(img, path)
        elif pil_fmt == "GIF":
            size = save_gif(img, path)
        elif pil_fmt == "BMP":
            size = save_bmp(img, path)
        else:
            img.save(path, pil_fmt)
            size = path.stat().st_size

    return path, size


def generate_one(
    fmt: str,
    width: int,
    height: int,
    output_dir: Path,
    prefix: str,
    target_size: Optional[int],
) -> tuple:
    """Generate a new test image and save in one format; return (path, size_bytes)."""
    img = make_image(width, height)
    return _save_one(img, fmt, output_dir, prefix, target_size, width, height)


def main() -> None:
    """CLI entry: generate test images or convert an existing image to selected formats."""
    parser = argparse.ArgumentParser(
        description="Generate test images in various formats and dimensions."
    )
    parser.add_argument(
        "-f", "--format",
        dest="formats",
        action="append",
        metavar="FMT",
        help="Format (e.g. png, jpeg, tiff, ico, pdf, heic). May be given multiple times.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        metavar="FMT",
        help="One or more formats (space-separated).",
    )
    parser.add_argument(
        "-W", "--width",
        type=int,
        default=800,
        help="Width in pixels (default 800).",
    )
    parser.add_argument(
        "-H", "--height",
        type=int,
        default=600,
        help="Height in pixels (default 600).",
    )
    parser.add_argument(
        "--target-size",
        type=str,
        metavar="SIZE",
        help="Target file size, e.g. 1024, 50kb, 1mb.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output"),
        help="Output directory (default ./output).",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="test_",
        help="Filename prefix (default test_).",
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        metavar="FILE",
        help="Convert existing image instead of generating. FILE: path to image (e.g. .jpg, .png).",
    )
    args = parser.parse_args()

    formats = list(args.formats) if args.formats else []
    if not formats:
        formats = ["png"]

    target_size = None
    if args.target_size:
        try:
            target_size = parse_size(args.target_size)
        except ValueError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)

    if args.input is not None:
        if not args.input.is_file():
            print(f"Error: input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        img = load_image(args.input)
        for fmt in formats:
            try:
                path, size = convert_one(img, fmt, args.output, args.prefix, target_size)
                print(f"  {path.name}  {size:,} bytes")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"  Error for {fmt}: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        for fmt in formats:
            try:
                path, size = generate_one(
                    fmt, args.width, args.height, args.output, args.prefix, target_size
                )
                print(f"  {path.name}  {size:,} bytes")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"  Error for {fmt}: {e}", file=sys.stderr)
                sys.exit(1)

    print(f"Done. Files in {args.output.absolute()}")


if __name__ == "__main__":
    main()
