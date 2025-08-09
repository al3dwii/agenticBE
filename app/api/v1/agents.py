# app/api/v1/agents.py

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_tenant
from app.core.rate_limit import check_rate_limit
from app.memory.redis import get_redis
from app.packs.registry import REGISTRY, get_registry

router = APIRouter()


def _get_agent_callable(pack: str, agent: str):
    """
    Resolve an agent function regardless of whether the project expects:
    - get_registry() -> { pack: { agent: callable } }  (new)
    - REGISTRY()     -> { pack: register_fn }          (legacy)
    """
    # Preferred: materialized mapping
    try:
        mapping = get_registry()  # { pack: { agent: callable } }
        entry = mapping.get(pack)
        if isinstance(entry, dict):
            fn = entry.get(agent)
            if callable(fn):
                return fn
    except Exception:
        pass

    # Fallback: legacy register function
    try:
        registers = REGISTRY()  # { pack: register_fn }
        reg_fn = registers.get(pack)
        if callable(reg_fn):
            pack_map = reg_fn()  # -> may be {"office": {...}} or just {...}
            if isinstance(pack_map, dict):
                inner = pack_map.get(pack, pack_map)
                if isinstance(inner, dict):
                    fn = inner.get(agent)
                    if callable(fn):
                        return fn
    except Exception:
        pass

    raise HTTPException(
        status_code=404,
        detail=f"Unknown agent '{pack}.{agent}'"
    )


@router.post("/agents/{pack}/{agent}")
async def run_agent(pack: str, agent: str, payload: dict, tenant=Depends(get_tenant)):
    # Rate limit per tenant
    await check_rate_limit(tenant.id, getattr(tenant, "user_id", None))

    # 1) Resolve the agent function (callable)
    agent_fn = _get_agent_callable(pack, agent)

    # 2) Build a minimal context the agent functions can use
    ctx = {
        "tenant_id": tenant.id,
        "user_id": getattr(tenant, "user_id", None),
        "redis": get_redis(),
    }

    # 3) Normalise inputs: prefer payload["inputs"], otherwise use top-level keys
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        # Back-compat: use top-level fields except known meta keys
        inputs = {k: v for k, v in payload.items() if k not in ("files", "webhook_url", "inputs")}

    # 4) Run the agent (our office agents are sync callables: agent_fn(ctx, inputs))
    try:
        result = agent_fn(ctx, inputs)
        # Return as JSON dict
        return result if isinstance(result, dict) else {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent error: {e}")


# from fastapi import APIRouter, Depends, HTTPException
# from app.core.auth import get_tenant
# from app.core.rate_limit import check_rate_limit
# from app.memory.redis import get_redis

# # 🔁 NEW: use the central registry instead of importer.load_agent
# from app.packs.registry import get_registry

# router = APIRouter()

# @router.post("/agents/{pack}/{agent}")
# async def run_agent(pack: str, agent: str, payload: dict, tenant=Depends(get_tenant)):
#     await check_rate_limit(tenant.id, tenant.user_id)

#     # Resolve the agent builder from the registry
#     try:
#         builder = get_registry().get(pack, agent)  # e.g. ("doc2deck","converter")
#     except KeyError as e:
#         raise HTTPException(status_code=404, detail=str(e))

#     # Build the runner/loop for this tenant (pass redis if your builder needs it)
#     runner = builder(get_redis(), tenant.id)

#     # Normalize payload
#     run_payload = {**payload, "tenant_id": tenant.id, "job_id": payload.get("job_id", "ad-hoc")}

#     # Run with robust invocation (supports .arun, .run, or callable coroutine)
#     try:
#         if hasattr(runner, "arun"):
#             result = await runner.arun(run_payload)
#         elif hasattr(runner, "run"):
#             maybe = runner.run(run_payload)
#             result = await maybe if hasattr(maybe, "__await__") else maybe
#         elif callable(runner):
#             maybe = runner(run_payload)
#             result = await maybe if hasattr(maybe, "__await__") else maybe
#         else:
#             raise TypeError("Agent builder returned an unsupported runner type")
#         return {"result": result}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Agent error: {e}")
