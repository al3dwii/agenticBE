import os

def route_model(ctx, task: str, tokens: int = 0) -> str:
    # placeholder; returned value is unused when we bypass
    return os.getenv("MODEL_FALLBACK", "gpt-4o-mini")

def run_structurer(model_name: str, outline, inputs):
    # Hard bypass so no imports or API keys are needed
    return outline
