import uuid, json
from sqlalchemy import select, text
from app.services.db import tenant_session
from app.memory.redis import get_redis
from app.models.event import Event

async def emit_event(tenant_id: str, job_id: str, step: str, status: str, payload: dict | None = None):
    eid = str(uuid.uuid4())
    async with tenant_session(tenant_id) as session:
        ev = Event(id=eid, tenant_id=tenant_id, job_id=job_id, step=step, status=status, payload_json=payload or {})
        session.add(ev)
        await session.commit()
    # SSE publish
    r = get_redis()
    message = json.dumps({"event":"step", "step": step, "status": status, "payload": payload or {}, "id": eid})
    await r.publish(f"jobs:{job_id}", message)
