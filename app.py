#!/usr/bin/env python3
# pylint: disable=import-error,broad-exception-caught,missing-docstring,line-too-long
"""
Local web UI for the test image generator.
Run: python app.py  then open http://127.0.0.1:5000 in a browser.
"""
import re
from pathlib import Path

from io import BytesIO

from flask import (
    Flask, request, jsonify, send_from_directory, render_template_string,
)
from PIL import Image

# Import generator logic (same as CLI)
from generate_images import generate_one, convert_one, FORMATS, HEIF_AVAILABLE, parse_size

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_BASE = BASE_DIR / "output"

# Format keys for UI (exclude duplicate jpg, j2k for shorter list)
FORMAT_CHOICES = [
    ("png", "PNG"),
    ("jpeg", "JPEG"),
    ("jpg", "JPG"),
    ("jfif", "JFIF"),
    ("gif", "GIF"),
    ("webp", "WebP"),
    ("bmp", "BMP"),
    ("tiff", "TIFF"),
    ("tif", "TIF"),
    ("ico", "ICO"),
    ("pdf", "PDF"),
    ("heic", "HEIC"),
    ("heif", "HEIF"),
    ("avif", "AVIF"),
    ("jp2", "JPEG 2000"),
    ("dib", "DIB"),
    ("icns", "ICNS"),
    ("ppm", "PPM"),
    ("tga", "TGA"),
    ("xbm", "XBM"),
]

# Accepted by the system (born-digital / standard); rest are for testing only
SYSTEM_ACCEPTED = {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif", "jfif", "avif", "heic", "heif", "ico", "pdf"}


def safe_subdir(name: str) -> str:
    """Allow only safe subdir names (no path traversal)."""
    if not name or not name.strip():
        return ""
    clean = re.sub(r"[^\w\-]", "", name.strip())
    return clean[:64] or ""


@app.route("/")
def index():
    """Render the main page with format choices and HEIF availability."""
    return render_template_string(
        INDEX_HTML,
        format_choices=FORMAT_CHOICES,
        heif_available=HEIF_AVAILABLE,
        system_accepted=SYSTEM_ACCEPTED,
    )


@app.route("/generate", methods=["POST"])
def generate():
    """Handle POST: generate test images or convert uploaded image to selected formats."""
    try:
        # Convert mode: file uploaded
        uploaded = request.files.get("input_image")
        if uploaded and uploaded.filename:
            formats = request.form.getlist("formats") or (request.form.get("formats") or "").split()
            if not formats:
                return jsonify(ok=False, error="Select at least one format"), 400
            try:
                img = Image.open(BytesIO(uploaded.read())).convert("RGB")
            except (OSError, ValueError) as e:
                return jsonify(ok=False, error=f"Invalid image: {e}"), 400
            target_size = None
            if request.form.get("target_size", "").strip():
                try:
                    target_size = parse_size(request.form.get("target_size", ""))
                except ValueError as e:
                    return jsonify(ok=False, error=str(e)), 400
            prefix = (request.form.get("prefix") or "test_").strip()[:32] or "test_"
            OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
            results = []
            for fmt in formats:
                fmt = fmt.lower().strip()
                if fmt not in FORMATS:
                    continue
                try:
                    path, size = convert_one(img, fmt, OUTPUT_BASE, prefix, target_size)
                    rel = path.relative_to(OUTPUT_BASE)
                    results.append({
                        "name": path.name,
                        "url": f"/download/{rel.as_posix()}",
                        "size": size,
                    })
                except (OSError, ValueError) as e:
                    return jsonify(ok=False, error=f"{fmt}: {e}"), 400
            if not results:
                return jsonify(ok=False, error="No files converted"), 400
            return jsonify(ok=True, files=results)

        # Generate mode: no file
        data = request.get_json(force=True, silent=True) or request.form
        formats = data.get("formats") or data.get("formats[]")
        if isinstance(formats, str):
            formats = [formats] if formats else []
        if not formats:
            return jsonify(ok=False, error="Select at least one format"), 400

        width = int(data.get("width", 800))
        height = int(data.get("height", 600))
        width = max(1, min(16000, width))
        height = max(1, min(16000, height))

        target_size = None
        if data.get("target_size", "").strip():
            try:
                target_size = parse_size(str(data.get("target_size", "")))
            except ValueError as e:
                return jsonify(ok=False, error=str(e)), 400

        prefix = (data.get("prefix") or "test_").strip()[:32] or "test_"
        output_dir = OUTPUT_BASE
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for fmt in formats:
            fmt = fmt.lower().strip()
            if fmt not in FORMATS:
                continue
            try:
                path, size = generate_one(fmt, width, height, output_dir, prefix, target_size)
                rel = path.relative_to(OUTPUT_BASE)
                results.append({
                    "name": path.name,
                    "url": f"/download/{rel.as_posix()}",
                    "size": size,
                })
            except (OSError, ValueError) as e:
                return jsonify(ok=False, error=f"{fmt}: {e}"), 400

        if not results:
            return jsonify(ok=False, error="No files generated"), 400
        return jsonify(ok=True, files=results)
    except Exception as e:  # pylint: disable=broad-exception-caught
        return jsonify(ok=False, error=str(e)), 500


@app.route("/download/<path:rel>")
def download(rel):
    """Serve a generated file from OUTPUT_BASE if path is inside it."""
    path = (OUTPUT_BASE / rel).resolve()
    try:
        path.relative_to(OUTPUT_BASE.resolve())
    except ValueError:
        return "Not found", 404
    if not path.is_file():
        return "Not found", 404
    return send_from_directory(path.parent, path.name, as_attachment=True, download_name=path.name)


INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <title>Test Image Generator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f0f12;
      --surface: #18181c;
      --border: #2a2a30;
      --text: #e4e4e7;
      --muted: #71717a;
      --accent: #a78bfa;
      --accent-hover: #c4b5fd;
      --success: #34d399;
      --error: #f87171;
    }
    * { box-sizing: border-box; }
    body {
      font-family: 'Outfit', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      margin: 0;
      padding: 2rem 1rem;
      line-height: 1.5;
    }
    .wrap { max-width: 520px; margin: 0 auto; }
    h1 {
      font-weight: 600;
      font-size: 1.5rem;
      margin: 0 0 1.5rem;
      letter-spacing: -0.02em;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    .card h2 {
      font-size: 0.75rem;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      margin: 0 0 1rem;
    }
    label { display: block; margin-bottom: 0.5rem; font-size: 0.9rem; color: var(--muted); }
    input[type="number"], input[type="text"], input[type="file"] {
      width: 100%;
      padding: 0.6rem 0.75rem;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      font: inherit;
      margin-bottom: 1rem;
    }
    input[type="file"] {
      cursor: pointer;
      padding: 0.75rem;
      border: 2px dashed var(--border);
      background: var(--surface);
    }
    input[type="file"]::file-selector-button {
      padding: 0.5rem 1rem;
      margin-right: 1rem;
      background: var(--accent);
      color: var(--bg);
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    input:focus { outline: none; border-color: var(--accent); }
    .row { display: flex; gap: 1rem; }
    .row > * { flex: 1; }
    .formats {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }
    .formats label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin: 0;
      cursor: pointer;
      font-size: 0.85rem;
      color: var(--text);
    }
    .formats input { width: auto; margin: 0; }
    .btn {
      width: 100%;
      padding: 0.75rem 1.25rem;
      background: var(--accent);
      color: var(--bg);
      border: none;
      border-radius: 8px;
      font: inherit;
      font-weight: 500;
      cursor: pointer;
      margin-top: 0.5rem;
    }
    .btn:hover { background: var(--accent-hover); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      display: block;
      width: 100%;
      min-width: 100%;
      box-sizing: border-box;
      background: var(--border);
      color: var(--text);
      padding: 0.75rem 1.25rem;
      margin-top: 0.5rem;
    }
    .btn-secondary:hover { background: #3a3a42; }
    .btn-full { width: 100%; margin-bottom: 0.5rem; }
    .btn-full button { width: 100%; }
    .row-align { align-items: flex-end; flex-wrap: wrap; }
    .hint { font-size: 0.8rem; color: var(--muted); margin: -0.5rem 0 1rem; }
    .muted { font-size: 0.85rem; color: var(--muted); margin-left: 0.5rem; }
    #result { margin-top: 1rem; }
    .files { margin-top: 0.75rem; }
    .files a {
      display: block;
      padding: 0.5rem 0;
      color: var(--accent);
      text-decoration: none;
      font-size: 0.9rem;
    }
    .files a:hover { text-decoration: underline; }
    .msg { padding: 0.75rem; border-radius: 8px; margin-top: 0.5rem; }
    .msg.err { background: rgba(248,113,113,0.15); color: var(--error); }
    .msg.ok { background: rgba(52,211,153,0.15); color: var(--success); }
    .size { color: var(--muted); font-size: 0.85em; }
    .formats label.format-accepted {
      background: rgba(52, 211, 153, 0.14);
      border: 1px solid rgba(52, 211, 153, 0.35);
      border-radius: 6px;
      padding: 0.4rem 0.6rem;
      color: #a7f3d0;
    }
    .formats label.format-testing {
      background: rgba(248, 113, 113, 0.1);
      border: 1px solid rgba(248, 113, 113, 0.28);
      border-radius: 6px;
      padding: 0.4rem 0.6rem;
      color: #fecaca;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Test Image Generator</h1>

    <form id="form" class="card">
      <h2>Format</h2>
      <div class="formats">
        {% for key, label in format_choices %}
        <label class="{% if key in system_accepted %}format-accepted{% else %}format-testing{% endif %}"><input type="checkbox" name="formats" value="{{ key }}"> {{ label }}</label>
        {% endfor %}
      </div>
      {% if not heif_available %}
      <p style="font-size:0.8rem; color: var(--muted);">HEIC/HEIF need <code>pip install pillow-heif</code></p>
      {% endif %}

      <h2>Convert existing image (optional)</h2>
      <label for="input_image">Upload a file to convert to the selected formats</label>
      <input type="file" name="input_image" id="input_image" accept="image/*">
      <p class="hint">JPG, PNG, etc. Leave empty to generate a new test image instead.</p>

      <h2>Dimensions (px)</h2>
      <div class="row">
        <div><label>Width</label><input type="number" name="width" value="800" min="1" max="16000"></div>
        <div><label>Height</label><input type="number" name="height" value="600" min="1" max="16000"></div>
      </div>
      <p class="hint">Used only when no image is uploaded.</p>

      <h2>Optional</h2>
      <label>Target file size (e.g. 50kb, 1mb, 5gb)</label>
      <p class="hint" style="margin-top:0.25rem;">Leave empty for default. This sets the output <strong>file size only</strong>. Units: 1 TB = 1024 GB = 1 048 576 MB = 1 073 741 824 KB = 1 099 511 627 776 bytes.</p>
      <input type="text" name="target_size" placeholder="Leave empty for default">

      <label>Where to save</label>
      <div class="btn-full">
        <button type="button" class="btn btn-secondary" id="pickFolderBtn" style="width:100%!important;max-width:100%;">Choose folder on this computer</button>
      </div>
      <p id="pickedFolderName" class="hint"></p>
      <p class="hint">Chrome/Edge: after generating, files are also written to the chosen folder.</p>

      <label>Filename prefix</label>
      <input type="text" name="prefix" value="test_" placeholder="test_">

      <button type="submit" class="btn" id="btn">Generate</button>
    </form>

    <div id="result"></div>
  </div>

  <script>
    const form = document.getElementById('form');
    const result = document.getElementById('result');
    const btn = document.getElementById('btn');
    const pickFolderBtn = document.getElementById('pickFolderBtn');
    const pickedFolderName = document.getElementById('pickedFolderName');
    let dirHandle = null;

    // Choose folder on this device (File System Access API – Chrome/Edge)
    pickFolderBtn.addEventListener('click', async () => {
      if (!('showDirectoryPicker' in window)) {
        pickedFolderName.textContent = '(Not supported in this browser. Use Chrome or Edge.)';
        return;
      }
      try {
        dirHandle = await window.showDirectoryPicker();
        pickedFolderName.textContent = dirHandle.name;
      } catch (err) {
        if (err.name !== 'AbortError') pickedFolderName.textContent = err.message || 'Error';
        else pickedFolderName.textContent = '';
      }
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const formats = fd.getAll('formats');
      if (!formats.length) {
        result.innerHTML = '<div class="msg err">Select at least one format.</div>';
        return;
      }
      btn.disabled = true;
      result.innerHTML = '';
      const hasFile = document.getElementById('input_image').files.length > 0;
      let r;
      if (hasFile) {
        r = await fetch('/generate', { method: 'POST', body: fd });
      } else {
        r = await fetch('/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
          formats,
          width: parseInt(fd.get('width') || 800, 10),
          height: parseInt(fd.get('height') || 600, 10),
          target_size: (fd.get('target_size') || '').trim() || undefined,
          prefix: (fd.get('prefix') || 'test_').trim()
        }) });
      }
      try {
        const data = await r.json();
        if (!r.ok) {
          result.innerHTML = '<div class="msg err">' + (data.error || 'Error') + '</div>';
          return;
        }
        if (dirHandle && data.files && data.files.length) {
          for (const f of data.files) {
            const res = await fetch(f.url);
            const blob = await res.blob();
            const fileHandle = await dirHandle.getFileHandle(f.name, { create: true });
            const w = await fileHandle.createWritable();
            await w.write(blob);
            await w.close();
          }
          result.innerHTML = '<div class="msg ok">Saved ' + data.files.length + ' file(s) to chosen folder and below.</div>';
        }
        let html = '<div class="card"><h2>Generated</h2><div class="files">';
        data.files.forEach(f => {
          html += '<a href="' + f.url + '" download>' + f.name + '</a> <span class="size">(' + (f.size || 0).toLocaleString() + ' B)</span><br>';
        });
        html += '</div></div>';
        result.innerHTML = (result.innerHTML || '') + html;
      } catch (err) {
        result.innerHTML = '<div class="msg err">' + err.message + '</div>';
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    # Use 5001: macOS Monterey+ often uses 5000 for AirPlay/Control Center
    app.run(host="127.0.0.1", port=5001, debug=False)
