import json
import os

from pywebpush import webpush, WebPushException


def send_push_notification(
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str = "Ulysses CRM",
    body: str = "New notification from Ulysses.",
    url: str = "/",
):
    private_key = (os.getenv("VAPID_PRIVATE_KEY") or "").strip()
    subject = (os.getenv("VAPID_SUBJECT") or "").strip()

    if not private_key:
        raise RuntimeError("VAPID_PRIVATE_KEY is not configured")

    if not subject:
        raise RuntimeError("VAPID_SUBJECT is not configured")

    subscription_info = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": p256dh,
            "auth": auth,
        },
    }

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
    })

    try:
        response = webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={
                "sub": subject,
            },
            ttl=60,
        )

        return response

    except WebPushException:
        raise