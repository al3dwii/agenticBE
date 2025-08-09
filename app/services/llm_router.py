import os
from app.services.llm import get_llm

DEFAULTS = {
    "structure": os.getenv("MODEL_STRUCTURE", "gpt-4o-mini"),
    "rewrite":   os.getenv("MODEL_REWRITE",   "claude-3-haiku"),
    "vision":    os.getenv("MODEL_VISION",    "gemini-1.5-pro"),
}

def route_model(ctx, task: str, tokens: int = 0) -> str:
    if task == "structure" and tokens > 12000:
        return os.getenv("MODEL_STRUCTURE_LONG", "gpt-4o")
    return DEFAULTS.get(task, os.getenv("MODEL_FALLBACK", "gpt-4o-mini"))

def run_structurer(model_name: str, outline, inputs):
    llm = get_llm(model_name)
    prompt = f"""Tighten and de-duplicate this slide outline.
    Keep sections <= {inputs.get('max_slides',12)}. Return JSON: [{{"title":"","bullets":["",""]}}]"""
    resp = llm.invoke(str(prompt) + "\n\n" + str(outline))
    try:
        import json; return json.loads(resp)
    except Exception:
        return outline
