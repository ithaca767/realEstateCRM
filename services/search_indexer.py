import logging
from typing import Optional, Tuple

from psycopg2.extras import RealDictCursor

from services.openai_client import call_embeddings_model


def build_contact_search_text(contact: dict) -> Tuple[str, str]:
    label = (contact.get("name") or "").strip()
    if not label:
        label = f"{(contact.get('first_name') or '').strip()} {(contact.get('last_name') or '').strip()}".strip()
    label = label.strip() or f"Contact {contact.get('id')}"

    parts = [
        label,
        (contact.get("email") or "").strip(),
        (contact.get("phone") or "").strip(),
        (contact.get("notes") or "").strip(),
    ]
    search_text = " \n".join([p for p in parts if p])
    return label, search_text


def upsert_search_index(
    conn,
    *,
    user_id: int,
    object_type: str,
    object_id: int,
    contact_id: Optional[int],
    label: str,
    search_text: str,
) -> bool:
    """
    Best-effort upsert. Returns True if upserted, False if skipped.
    Never raises unless DB itself is unavailable.
    """
    label = (label or "").strip()
    search_text = (search_text or "").strip()
    if not label or not search_text:
        return False

    try:
        emb = call_embeddings_model(search_text)
    except Exception:
        logging.exception(
            "Embeddings unavailable (object_type=%s object_id=%s user_id=%s)",
            object_type,
            object_id,
            user_id,
        )
        return False

    if not emb:
        return False

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        INSERT INTO search_index
            (user_id, object_type, object_id, contact_id, label, search_text, embedding, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id, object_type, object_id)
        DO UPDATE SET
            contact_id = EXCLUDED.contact_id,
            label = EXCLUDED.label,
            search_text = EXCLUDED.search_text,
            embedding = EXCLUDED.embedding,
            updated_at = NOW()
        """,
        (user_id, object_type, object_id, contact_id, label, search_text, emb),
    )
    return True


def delete_search_index_row(conn, *, user_id: int, object_type: str, object_id: int) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM search_index
        WHERE user_id = %s AND object_type = %s AND object_id = %s
        """,
        (user_id, object_type, object_id),
    )
