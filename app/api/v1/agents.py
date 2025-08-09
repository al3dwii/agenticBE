from __future__ import annotations

import inspect
from fastapi import APIRouter, Depends, HTTPException, Body

from app.core.auth import get_tenant
from app.core.rate_limit import check_rate_limit
from app.memory.redis import get_redis
from app.packs.registry import get_registry

router = APIRouter()


@router.post("/agents/{pack}/{agent}")
async def run_agent(
    pack: str,
    agent: str,
    payload: dict = Body(...),
    tenant=Depends(get_tenant),
):
    # simple rate-limit hook
    await check_rate_limit(tenant.id, tenant.user_id)

    # 1) resolve builder
    reg = get_registry()  # { pack: { agent: builder } }
    pack_map = reg.get(pack)
    if not isinstance(pack_map, dict):
        raise HTTPException(status_code=404, detail=f"Unknown pack '{pack}'")

    builder = pack_map.get(agent)
    if not callable(builder):
        raise HTTPException(status_code=404, detail=f"Unknown agent '{pack}.{agent}'")

    # 2) build runner
    try:
        runner = builder(get_redis(), tenant.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent init error: {e}")

    # 3) execute runner (prefer async .arun)
    enriched = {**payload, "tenant_id": tenant.id, "job_id": payload.get("job_id", "ad-hoc")}

    try:
        if hasattr(runner, "arun") and inspect.iscoroutinefunction(runner.arun):
            result = await runner.arun(enriched)
        elif hasattr(runner, "run"):
            maybe = runner.run(enriched)
            result = await maybe if inspect.iscoroutine(maybe) else maybe
        elif callable(runner):
            maybe = runner(enriched)
            result = await maybe if inspect.iscoroutine(maybe) else maybe
        else:
            raise TypeError("Runner is not callable")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent error: {e}")

    # 4) return the dict produced by the agent
    return result




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
