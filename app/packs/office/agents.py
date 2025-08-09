from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

from app.tools.office_io import (
    fetch_to_tmp,
    pdf_to_outline,
    docx_to_outline,
    pptx_to_outline,
    outline_to_pptx,
    build_pptx_from_pdf,
    build_pptx_from_docx,
    pptx_to_pdf_file,
    pptx_to_docx_file,
    pptx_to_html5_zip,
    save_artifact,
)


class _Runner:
    """Tiny async-compatible wrapper around a sync function."""
    def __init__(self, fn):
        self._fn = fn

    async def arun(self, inputs: Dict[str, Any]):
        return self._fn(inputs)


def _save_once(path: str, name: str) -> Tuple[str, str]:
    key, url = save_artifact(path, name)
    return key, url


# ----------------- Builders -----------------

def pdf_to_pptx_builder(_redis, _tenant_id):
    def run(inputs: Dict[str, Any]):
        local = fetch_to_tmp(inputs)
        title = inputs.get("title")
        max_slides = int(inputs.get("max_slides", 12))
        outline = pdf_to_outline(local, max_slides=max_slides)
        pptx_path = outline_to_pptx(outline, title=title)
        key, url = _save_once(pptx_path, "slides.pptx")
        return {"pptx_key": key, "pptx_url": url, "outline": outline}
    return _Runner(run)


def word_to_pptx_builder(_redis, _tenant_id):
    def run(inputs: Dict[str, Any]):
        local = fetch_to_tmp(inputs)
        title = inputs.get("title")
        max_slides = int(inputs.get("max_slides", 12))
        outline = docx_to_outline(local, max_slides=max_slides)
        pptx_path = outline_to_pptx(outline, title=title)
        key, url = _save_once(pptx_path, "slides.pptx")
        return {"pptx_key": key, "pptx_url": url, "outline": outline}
    return _Runner(run)


def pptx_to_pdf_builder(_redis, _tenant_id):
    def run(inputs: Dict[str, Any]):
        local = fetch_to_tmp(inputs)
        pdf_path = pptx_to_pdf_file(local)
        key, url = _save_once(pdf_path, "slides.pdf")
        return {"pdf_key": key, "pdf_url": url}
    return _Runner(run)


def pptx_to_docx_builder(_redis, _tenant_id):
    def run(inputs: Dict[str, Any]):
        local = fetch_to_tmp(inputs)
        docx_path = pptx_to_docx_file(local)
        key, url = _save_once(docx_path, "slides.docx")
        return {"docx_key": key, "docx_url": url}
    return _Runner(run)


def pptx_to_html5_builder(_redis, _tenant_id):
    def run(inputs: Dict[str, Any]):
        local = fetch_to_tmp(inputs)
        zip_path = pptx_to_html5_zip(local)
        key, url = _save_once(zip_path, "slides_html.zip")
        return {"zip_key": key, "zip_url": url}
    return _Runner(run)

# from typing import Dict, Any
# from pathlib import Path
# import shutil, tempfile, os, zipfile

# from app.services.llm_router import route_model, run_structurer
# try:
#     from app.services.artifacts import save_file_and_url
# except Exception:
#     # fallback simple saver if project lacks artifacts service
#     def save_file_and_url(ctx, path, content_type="application/octet-stream", is_directory=False):
#         artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/tmp/artifacts")
#         public_base = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8080")
#         Path(artifacts_dir).mkdir(parents=True, exist_ok=True)
#         if is_directory:
#             # zip the dir
#             zpath = Path(tempfile.mkdtemp()) / (Path(path).name + ".zip")
#             with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
#                 for root, _, files in os.walk(path):
#                     for f in files:
#                         p = Path(root)/f
#                         zf.write(p, p.relative_to(path))
#             out = Path(artifacts_dir)/zpath.name
#             shutil.move(str(zpath), out)
#         else:
#             out = Path(artifacts_dir)/Path(path).name
#             shutil.copy2(path, out)
#         url = f"{public_base.rstrip('/')}/artifacts/{out.name}"
#         return str(out), url

# from app.tools.office_io import (
#     fetch_to_tmp, docx_to_outline, pdf_to_outline, outline_to_pptx, soffice_convert
# )

# def _mk_title(inputs): return inputs.get("title") or "Converted Presentation"

# def word_to_pptx(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
#     src = fetch_to_tmp(inputs)
#     outline = docx_to_outline(src)
#     outline = run_structurer(route_model(ctx,"structure"), outline, inputs)
#     out = str(Path(tempfile.mkdtemp()) / "slides.pptx")
#     outline_to_pptx(outline[:inputs.get("max_slides", 12)], out, _mk_title(inputs))
#     key, url = save_file_and_url(ctx, out, content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
#     return {"pptx_key": key, "pptx_url": url, "outline": outline}

# def pdf_to_pptx(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
#     src = fetch_to_tmp(inputs)
#     outline = pdf_to_outline(src)
#     outline = run_structurer(route_model(ctx,"structure"), outline, inputs)
#     out = str(Path(tempfile.mkdtemp()) / "slides.pptx")
#     outline_to_pptx(outline[:inputs.get("max_slides", 12)], out, _mk_title(inputs))
#     key, url = save_file_and_url(ctx, out, content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
#     return {"pptx_key": key, "pptx_url": url, "outline": outline}

# def pptx_to_pdf(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
#     src = fetch_to_tmp(inputs)
#     out = str(Path(tempfile.mkdtemp()) / "slides.pdf")
#     pdf = soffice_convert(src, "pdf:writer_pdf_Export", str(Path(out).parent))
#     if pdf != out:
#         shutil.move(pdf, out)
#     key, url = save_file_and_url(ctx, out, content_type="application/pdf")
#     return {"pdf_key": key, "pdf_url": url}

# def pptx_to_html5(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
#     # Very simple Reveal.js export (text only). For richer fidelity, add images later.
#     from pptx import Presentation
#     src = fetch_to_tmp(inputs)
#     prs = Presentation(src)
#     html = ["<!doctype html><html><head><meta charset='utf-8'>"
#             "<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/reveal.js/dist/reveal.css'>"
#             "<script src='https://cdn.jsdelivr.net/npm/reveal.js/dist/reveal.js'></script></head>"
#             "<body><div class='reveal'><div class='slides'>"]
#     for s in prs.slides:
#         texts = []
#         for shape in s.shapes:
#             if hasattr(shape, "text") and shape.text:
#                 texts.append(shape.text)
#         title = texts[0] if texts else ""
#         body = "<br>".join(texts[1:]) if len(texts)>1 else ""
#         html.append(f"<section><h3>{title}</h3><p>{body}</p></section>")
#     html.append("</div></div><script>Reveal.initialize();</script></body></html>")
#     tmpdir = Path(tempfile.mkdtemp())
#     (tmpdir/"index.html").write_text("".join(html))
#     key, url = save_file_and_url(ctx, str(tmpdir), is_directory=True, content_type="application/zip")
#     return {"html5_key": key, "html5_url": url}

# def pptx_to_docx(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
#     # Extract text -> minimal DOCX via pandoc (markdown -> docx)
#     from pptx import Presentation
#     src = fetch_to_tmp(inputs)
#     prs = Presentation(src)
#     lines = []
#     for s in prs.slides:
#         slide_lines = []
#         for shape in s.shapes:
#             if hasattr(shape, "text") and shape.text:
#                 slide_lines.append(shape.text.strip())
#         if slide_lines:
#             lines.append("# " + slide_lines[0])
#             for b in slide_lines[1:]:
#                 lines.append(f"- {b}")
#             lines.append("")
#     md = "\n".join(lines) if lines else "# Slides\n"
#     md_path = Path(tempfile.mkdtemp()) / "slides.md"
#     md_path.write_text(md)
#     docx_path = Path(tempfile.mkdtemp()) / "slides.docx"
#     import subprocess
#     subprocess.run(["pandoc", str(md_path), "-o", str(docx_path)], check=True)
#     key, url = save_file_and_url(ctx, str(docx_path), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
#     return {"docx_key": key, "docx_url": url}
