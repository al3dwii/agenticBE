import hmac, hashlib, json, uuid
from typing import Any, Dict
from app.core.config import settings
from app.services.db import tenant_session
from app.models.webhook_delivery import WebhookDelivery

def sign_payload(payload: Dict[str, Any]) -> str:
    secret = (settings.__dict__.get("WEBHOOK_HMAC_SECRET") or "change-me").encode()
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

async def enqueue_delivery(tenant_id: str, job_id: str, url: str, event_type: str, payload: Dict[str, Any]):
    delivery_id = str(uuid.uuid4())
    async with tenant_session(tenant_id) as session:
        d = WebhookDelivery(
            id=delivery_id,
            tenant_id=tenant_id,
            job_id=job_id,
            url=url,
            event_type=event_type,
            payload_json=payload,
            status="pending",
            attempts=0,
        )
        session.add(d)
        await session.commit()
    # Dispatch Celery task
    from app.workers.celery_app import deliver_webhook
    deliver_webhook.delay(delivery_id)
    return delivery_id
