from .agents import (
    word_to_pptx, pptx_to_docx, pdf_to_pptx,
    pptx_to_pdf, pptx_to_html5
)

def register():
    return {
        "office": {
            "word_to_pptx": word_to_pptx,
            "pptx_to_docx": pptx_to_docx,
            "pdf_to_pptx": pdf_to_pptx,
            "pptx_to_pdf": pptx_to_pdf,
            "pptx_to_html5": pptx_to_html5,
        }
    }
