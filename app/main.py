from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.observability import setup_otel
from app.core.metrics import MetricsMiddleware, metrics_app
from app.api.v1 import agents, jobs, events
from app.services.db import init_models

import os
from app.packs import registry as _packs_registry  # noqa: F401


app = FastAPI(title="Agentic Backend", version="1.0.0")
app.add_middleware(MetricsMiddleware)

# Make sure the artifacts dir exists at startup
os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)

app.mount(
    "/artifacts",
    StaticFiles(directory=settings.ARTIFACTS_DIR, check_dir=False),  # <- no crash if missing
    name="artifacts",
)

setup_otel(app)

@app.get("/health")
async def health():
    return JSONResponse({"ok": True, "env": settings.ENV})

# (unchanged) API routers
app.include_router(agents.router, prefix="/v1", tags=["agents"])
app.include_router(jobs.router,   prefix="/v1", tags=["jobs"])
app.include_router(events.router, prefix="/v1", tags=["events"])

@app.on_event("startup")
async def on_startup():
    await init_models()

# Prometheus metrics
app.mount("/metrics", metrics_app)

# 👇 Optional: debug endpoint to see what agents are registered (remove in prod)
try:
    from app.packs.registry import REGISTRY

    @app.get("/v1/packs")
    async def list_packs():
        return REGISTRY.list()
except Exception:
    pass
