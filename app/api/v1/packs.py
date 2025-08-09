from fastapi import APIRouter
from app.packs.registry import get_registry

router = APIRouter()

@router.get("/v1/packs")
def list_packs():
    reg = get_registry()
    # return a JSON-serializable structure
    return {pack: sorted(list(agents.keys())) for pack, agents in reg.items()}
