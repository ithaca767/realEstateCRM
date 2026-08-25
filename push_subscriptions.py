def save_push_subscription(
    conn,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
):
    """
    Create or refresh one browser/device push subscription.

    A subscription endpoint may belong to only one Ulysses user.
    """
    if not user_id:
        raise ValueError("user_id is required")

    endpoint = (endpoint or "").strip()
    p256dh = (p256dh or "").strip()
    auth = (auth or "").strip()

    if not endpoint or not p256dh or not auth:
        raise ValueError("endpoint, p256dh, and auth are required")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id
            FROM push_subscriptions
            WHERE endpoint = %s
            """,
            (endpoint,),
        )
        existing = cur.fetchone()

        if existing and existing["user_id"] != user_id:
            raise ValueError(
                "This push subscription belongs to another user."
            )

        cur.execute(
            """
            INSERT INTO push_subscriptions (
                user_id,
                endpoint,
                p256dh,
                auth,
                is_active,
                created_at,
                updated_at,
                last_seen_at
            )
            VALUES (
                %s, %s, %s, %s,
                TRUE,
                NOW(),
                NOW(),
                NOW()
            )
            ON CONFLICT (endpoint)
            DO UPDATE SET
                p256dh = EXCLUDED.p256dh,
                auth = EXCLUDED.auth,
                is_active = TRUE,
                updated_at = NOW(),
                last_seen_at = NOW()
            RETURNING id
            """,
            (
                user_id,
                endpoint,
                p256dh,
                auth,
            ),
        )

        row = cur.fetchone()

    return row["id"]
    
def deactivate_push_subscription(
    conn,
    user_id: int,
    endpoint: str,
):
    """
    Deactivate one browser/device push subscription.
    """
    if not user_id:
        raise ValueError("user_id is required")

    endpoint = (endpoint or "").strip()

    if not endpoint:
        raise ValueError("endpoint is required")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE push_subscriptions
            SET
                is_active = FALSE,
                updated_at = NOW(),
                last_seen_at = NOW()
            WHERE user_id = %s
              AND endpoint = %s
            RETURNING id
            """,
            (user_id, endpoint),
        )

        row = cur.fetchone()

    return row["id"] if row else None
