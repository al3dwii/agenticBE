import os, json, asyncio, inspect
from celery import Celery
from app.core.config import settings

# 🔁 Ensure pack registrations exist in the worker process
from app.packs import registry as _packs_registry  # side-effect import
from app.packs.registry import REGISTRY

celery = Celery("agentic")
celery.conf.broker_url = settings.REDIS_URL_QUEUE
celery.conf.result_backend = settings.REDIS_URL_QUEUE

@celery.task(name="run_agent_job", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_agent_job(tenant_id: str, pack: str, agent: str, payload: dict, job_id: str, webhook_url: str | None = None):
    from sqlalchemy import select, text
    from app.memory.redis import get_redis
    from app.services.db import SessionLocal
    from app.models.job import Job
    from app.services.webhooks import enqueue_delivery

    async def _run():
        r = get_redis()
        await r.publish(f"jobs:{job_id}", json.dumps({"event": "started"}))

        result = None
        error = None

        # Resolve agent via the registry
        try:
            builder = REGISTRY.get(pack, agent)              # e.g., ("doc2deck", "converter")
            runner  = builder(r, tenant_id)                  # returns async callable / runner
        except Exception as e:
            error = f"Unknown agent {pack}/{agent}: {e}"
            runner = None

        if runner is not None and error is None:
            enriched = {**payload, "tenant_id": tenant_id, "job_id": job_id}
            try:
                if hasattr(runner, "arun"):
                    result = await runner.arun(enriched)
                elif hasattr(runner, "run"):
                    maybe = runner.run(enriched)
                    result = await maybe if inspect.isawaitable(maybe) else maybe
                elif callable(runner):
                    maybe = runner(enriched)
                    result = await maybe if inspect.isawaitable(maybe) else maybe
                else:
                    error = "Agent runner type is not supported"
            except Exception as e:
                error = str(e)

        # Persist job status + fire webhooks
        async with SessionLocal() as session:
            # Set tenant context using set_config (LOCAL scope)
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": tenant_id},
            )
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one_or_none()
            if job:
                if error:
                    job.status = "failed"
                    job.error = error
                    await r.publish(f"jobs:{job_id}", json.dumps({"event": "failed", "error": error}))
                    if webhook_url:
                        await enqueue_delivery(
                            tenant_id, job_id, webhook_url, "job.failed",
                            {"job_id": job_id, "error": error}
                        )
                else:
                    job.status = "succeeded"
                    job.output_json = {"result": result}
                    await r.publish(f"jobs:{job_id}", json.dumps({"event": "succeeded"}))
                    if webhook_url:
                        await enqueue_delivery(
                            tenant_id, job_id, webhook_url, "job.succeeded",
                            {"job_id": job_id, "result": result}
                        )
                await session.commit()

    asyncio.run(_run())

@celery.task(name="deliver_webhook", bind=True, max_retries=6, default_retry_delay=30)
def deliver_webhook(self, delivery_id: str):
    import httpx
    from sqlalchemy import select, text
    from app.services.db import SessionLocal
    from app.models.webhook_delivery import WebhookDelivery
    from app.services.webhooks import sign_payload

    async def _send():
        async with SessionLocal() as session:
            # We fetch the delivery first to learn the tenant_id
            res = await session.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
            d = res.scalar_one_or_none()
            if not d:
                return

            # Then set the tenant context
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": d.tenant_id},
            )

            payload = d.payload_json
            sig = sign_payload(payload)
            try:
                async with httpx.AsyncClient(timeout=20) as c:
                    r = await c.post(
                        d.url,
                        json=payload,
                        headers={
                            "X-Agentic-Event": d.event_type,
                            "X-Agentic-Signature": sig,
                            "Content-Type": "application/json",
                        },
                    )
                    if 200 <= r.status_code < 300:
                        d.status = "sent"
                        d.attempts += 1
                        d.last_error = None
                        await session.commit()
                        return
                    raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                d.status = "retrying"
                d.attempts += 1
                d.last_error = str(e)
                await session.commit()
                raise

    try:
        asyncio.run(_send())
    except Exception as exc:
        # exponential backoff, capped by Celery's retry settings
        raise self.retry(exc=exc, countdown=min(600, 2 ** self.request.retries * 10))


# import os, json, asyncio, inspect
# from celery import Celery
# from app.core.config import settings

# # 🔁 Ensure pack registrations exist in the worker process
# from app.packs import registry as _packs_registry  # side-effect import
# from app.packs.registry import REGISTRY

# celery = Celery("agentic")
# celery.conf.broker_url = settings.REDIS_URL_QUEUE
# celery.conf.result_backend = settings.REDIS_URL_QUEUE

# @celery.task(name="run_agent_job", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
# def run_agent_job(tenant_id: str, pack: str, agent: str, payload: dict, job_id: str, webhook_url: str | None = None):
#     from sqlalchemy import select, text
#     from app.memory.redis import get_redis
#     from app.services.db import SessionLocal
#     from app.models.job import Job
#     from app.services.webhooks import enqueue_delivery

#     async def _run():
#         r = get_redis()
#         await r.publish(f"jobs:{job_id}", json.dumps({"event": "started"}))

#         result = None
#         error = None

#         # Resolve agent via the registry
#         try:
#             builder = REGISTRY.get(pack, agent)              # e.g., ("doc2deck", "converter")
#             runner  = builder(r, tenant_id)                  # returns async callable / runner
#         except Exception as e:
#             error = f"Unknown agent {pack}/{agent}: {e}"
#             runner = None

#         if runner is not None and error is None:
#             enriched = {**payload, "tenant_id": tenant_id, "job_id": job_id}
#             try:
#                 if hasattr(runner, "arun"):
#                     result = await runner.arun(enriched)
#                 elif hasattr(runner, "run"):
#                     maybe = runner.run(enriched)
#                     result = await maybe if inspect.isawaitable(maybe) else maybe
#                 elif callable(runner):
#                     maybe = runner(enriched)
#                     result = await maybe if inspect.isawaitable(maybe) else maybe
#                 else:
#                     error = "Agent runner type is not supported"
#             except Exception as e:
#                 error = str(e)

#         # Persist job status + fire webhooks (unchanged)
#         async with SessionLocal() as session:
#             await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
#             res = await session.execute(select(Job).where(Job.id == job_id))
#             job = res.scalar_one_or_none()
#             if job:
#                 if error:
#                     job.status = "failed"
#                     job.error = error
#                     await r.publish(f"jobs:{job_id}", json.dumps({"event": "failed", "error": error}))
#                     if webhook_url:
#                         await enqueue_delivery(
#                             tenant_id, job_id, webhook_url, "job.failed",
#                             {"job_id": job_id, "error": error}
#                         )
#                 else:
#                     job.status = "succeeded"
#                     job.output_json = {"result": result}
#                     await r.publish(f"jobs:{job_id}", json.dumps({"event": "succeeded"}))
#                     if webhook_url:
#                         await enqueue_delivery(
#                             tenant_id, job_id, webhook_url, "job.succeeded",
#                             {"job_id": job_id, "result": result}
#                         )
#                 await session.commit()

#     asyncio.run(_run())

# @celery.task(name="deliver_webhook", bind=True, max_retries=6, default_retry_delay=30)
# def deliver_webhook(self, delivery_id: str):
#     import httpx
#     from sqlalchemy import select, text
#     from app.services.db import SessionLocal
#     from app.models.webhook_delivery import WebhookDelivery
#     from app.services.webhooks import sign_payload

#     async def _send():
#         async with SessionLocal() as session:
#             res = await session.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
#             d = res.scalar_one_or_none()
#             if not d:
#                 return
#             await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": d.tenant_id})

#             payload = d.payload_json
#             sig = sign_payload(payload)
#             try:
#                 async with httpx.AsyncClient(timeout=20) as c:
#                     r = await c.post(
#                         d.url,
#                         json=payload,
#                         headers={
#                             "X-Agentic-Event": d.event_type,
#                             "X-Agentic-Signature": sig,
#                             "Content-Type": "application/json",
#                         },
#                     )
#                     if 200 <= r.status_code < 300:
#                         d.status = "sent"
#                         d.attempts += 1
#                         d.last_error = None
#                         await session.commit()
#                         return
#                     raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
#             except Exception as e:
#                 d.status = "retrying"
#                 d.attempts += 1
#                 d.last_error = str(e)
#                 await session.commit()
#                 raise

#     try:
#         asyncio.run(_send())
#     except Exception as exc:
#         # exponential backoff, capped by Celery's retry settings
#         raise self.retry(exc=exc, countdown=min(600, 2 ** self.request.retries * 10))
