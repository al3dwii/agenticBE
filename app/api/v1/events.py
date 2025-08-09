from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import asyncio, json
from app.core.auth import get_tenant
from app.memory.redis import get_redis

router = APIRouter()

@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str, tenant=Depends(get_tenant)):
    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"jobs:{job_id}"

    async def event_generator():
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message and message.get("type") == "message":
                    data = message["data"]
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode("utf-8")
                    yield f"data: {data}\n\n"
                await asyncio.sleep(0.1)
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
