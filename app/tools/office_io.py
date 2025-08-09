import os, shutil, subprocess, tempfile
from pathlib import Path
from typing import List, Dict, Any
import urllib.request

import mammoth
from pdfminer.high_level import extract_text
from pptx import Presentation

def _run(cmd: List[str]):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{p.stderr}")
    return p.stdout

def fetch_to_tmp(inputs: Dict[str, Any]) -> str:
    # Supports file_url | source_url | file_path
    url = inputs.get("file_url") or inputs.get("source_url")
    if url:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        urllib.request.urlretrieve(url, path)
        return path
    if inputs.get("file_path") and os.path.exists(inputs["file_path"]):
        tmp = Path(tempfile.mkdtemp()) / Path(inputs["file_path"]).name
        shutil.copy2(inputs["file_path"], tmp)
        return str(tmp)
    raise ValueError("Provide file_url/source_url or file_path.")

def docx_to_outline(docx_path: str) -> List[Dict[str, Any]]:
    with open(docx_path, "rb") as f:
        html = mammoth.convert_to_html(f).value
    sections = [s.strip() for s in html.split("<h") if "</h" in s]
    outline = []
    for s in sections:
        title = s.split(">",1)[1].split("</h",1)[0].strip()
        bullets = []
        if "<li>" in s:
            bullets = [x.split("</li>",1)[0] for x in s.split("<li>")[1:]]
        outline.append({"title": title, "bullets": bullets[:6]})
    return outline[:24]

def pdf_to_outline(pdf_path: str) -> List[Dict[str, Any]]:
    text = extract_text(pdf_path) or ""
    chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 40]
    return [{"title": c.split("\n")[0][:80], "bullets": c.split("\n")[1:6]} for c in chunks[:20]]

def outline_to_pptx(outline: List[Dict[str, Any]], out_path: str, title: str = None):
    prs = Presentation()
    if title:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = title
        slide.placeholders[1].text = ""
    for sec in outline:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = sec.get("title","")[:120]
        tf = slide.placeholders[1].text_frame
        try:
            tf.clear()
        except Exception:
            pass
        for b in sec.get("bullets", [])[:12]:
            p = tf.add_paragraph(); p.text = str(b)[:200]; p.level = 0
    prs.save(out_path)
    return out_path

def soffice_convert(inp: str, fmt: str, outdir: str) -> str:
    Path(outdir).mkdir(parents=True, exist_ok=True)
    _run(["soffice","--headless","--convert-to",fmt,"--outdir",outdir,inp])
    base = Path(inp).with_suffix(f".{fmt.split(':')[0]}")
    return str(Path(outdir)/base.name)
