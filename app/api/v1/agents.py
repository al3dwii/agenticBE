from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import get_tenant
from app.core.rate_limit import check_rate_limit
from app.memory.redis import get_redis
from app.packs.registry import get_registry

router = APIRouter()

@router.post("/agents/{pack}/{agent}")
async def run_agent(pack: str, agent: str, payload: dict, tenant=Depends(get_tenant)):
    await check_rate_limit(tenant.id, tenant.user_id)

    # 1) resolve builder from registry
    try:
        builder = get_registry().get(pack, agent)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{pack}.{agent}': {e}")
    except Exception as e:
        # Anything weird during import/registry
        raise HTTPException(status_code=400, detail=f"Agent load error: {e}")

    # 2) build the runner (this may raise too)
    try:
        runner = builder(get_redis(), tenant.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent init error: {e}")

    # 3) actually run the agent
    try:
        result = await runner.arun({**payload, "tenant_id": tenant.id, "job_id": payload.get("job_id","ad-hoc")})
        return {"result": result}
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
