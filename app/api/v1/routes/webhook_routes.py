from fastapi import APIRouter, Request, HTTPException, status
import os

from app.core.logger import get_logger

logger = get_logger("webhook_routes")
router = APIRouter()

# Clerk webhook secret for verification
CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET")

async def verify_clerk_webhook(request: Request) -> dict:
    """Verify Clerk webhook signature and return payload"""
    # In production, you should verify the webhook signature
    # For now, we'll trust the payload
    try:
        body = await request.json()
        return body
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload"
        )

@router.post("/webhooks/clerk", tags=["Webhooks"])
async def clerk_webhook(request: Request):
    """
    Handle Clerk webhooks for user events.
    Events: user.created, user.updated, invitation.accepted
    """
    payload = await verify_clerk_webhook(request)
    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"Received Clerk webhook: {event_type}")

    if event_type == "user.created":
        email_addresses = data.get("email_addresses") or []
        primary_email = None

        for email_obj in email_addresses:
            if email_obj.get("id") == data.get("primary_email_address_id"):
                primary_email = email_obj.get("email_address")
                break

        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")

        logger.info(
            "Clerk user.created webhook processed",
            extra={
                "clerk_user_id": data.get("id"),
                "email": primary_email,
            },
        )
    else:
        logger.info("No handler for webhook event; skipping.", extra={"event": event_type})

    return {"status": "success"}
