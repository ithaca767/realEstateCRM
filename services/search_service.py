from psycopg2.extras import RealDictCursor


def _normalize_query(q: str) -> str:
    return (q or "").strip()


def search_contacts(conn, user_id: int, q: str, limit: int = 20):
    q = _normalize_query(q)
    if len(q) < 2:
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            c.id,
            COALESCE(NULLIF(c.name, ''), CONCAT_WS(' ', c.first_name, c.last_name)) AS label,
            ts_rank(
                setweight(to_tsvector('english', COALESCE(c.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(c.first_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(c.last_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(c.email, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(c.phone, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(c.notes, '')), 'C'),
                websearch_to_tsquery('english', %s)
            ) AS score,
            left(COALESCE(c.notes, ''), 240) AS snippet
        FROM contacts c
        WHERE c.user_id = %s
          AND (
            setweight(to_tsvector('english', COALESCE(c.name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(c.first_name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(c.last_name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(c.email, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(c.phone, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(c.notes, '')), 'C')
          ) @@ websearch_to_tsquery('english', %s)
        ORDER BY score DESC, c.last_name NULLS LAST, c.first_name NULLS LAST, c.id DESC
        LIMIT %s
        """,
        (q, user_id, q, limit),
    )

    rows = cur.fetchall() or []
    out = []
    for r in rows:
        out.append({
            "type": "contact",
            "id": r["id"],
            "label": r.get("label") or f"Contact {r['id']}",
            "snippet": (r.get("snippet") or "").strip(),
            "score": float(r.get("score") or 0),
        })
    return out


def search_engagements(conn, user_id: int, q: str, limit: int = 30):
    q = _normalize_query(q)
    if len(q) < 2:
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            e.id,
            e.contact_id,
            e.occurred_at,
            e.engagement_type,
            COALESCE(
                NULLIF(e.summary_clean, ''),
                NULLIF(e.notes, ''),
                NULLIF(e.transcript_raw, ''),
                ''
            ) AS best_text,
            ts_rank(
                setweight(to_tsvector('english', COALESCE(e.engagement_type, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(e.summary_clean, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(e.notes, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(e.transcript_raw, '')), 'C'),
                websearch_to_tsquery('english', %s)
            ) AS score
        FROM engagements e
        WHERE e.user_id = %s
          AND (
            setweight(to_tsvector('english', COALESCE(e.engagement_type, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(e.summary_clean, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(e.notes, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(e.transcript_raw, '')), 'C')
          ) @@ websearch_to_tsquery('english', %s)
        ORDER BY score DESC, e.occurred_at DESC NULLS LAST, e.id DESC
        LIMIT %s
        """,
        (q, user_id, q, limit),
    )

    rows = cur.fetchall() or []
    out = []
    for r in rows:
        occurred = r.get("occurred_at")
        occurred_label = occurred.date().isoformat() if occurred else ""
        etype = (r.get("engagement_type") or "").replace("_", " ").title()
        label = f"{etype} {occurred_label}".strip() if (etype or occurred_label) else f"Engagement {r['id']}"

        snippet = (r.get("best_text") or "").strip()
        if len(snippet) > 260:
            snippet = snippet[:260].rstrip() + "…"

        out.append({
            "type": "engagement",
            "id": r["id"],
            "contact_id": r.get("contact_id"),
            "label": label,
            "snippet": snippet,
            "score": float(r.get("score") or 0),
        })
    return out

def search_professionals(conn, user_id: int, q: str, limit: int = 20):
    q = _normalize_query(q)
    if len(q) < 2:
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            p.id,
            p.name,
            p.company,
            p.category,
            ts_rank(
                setweight(to_tsvector('english', COALESCE(p.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(p.company, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(p.category, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(p.notes, '')), 'C'),
                websearch_to_tsquery('english', %s)
            ) AS score,
            left(COALESCE(p.notes, ''), 240) AS snippet
        FROM professionals p
        WHERE p.user_id = %s
          AND (
            setweight(to_tsvector('english', COALESCE(p.name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(p.company, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(p.category, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(p.notes, '')), 'C')
          ) @@ websearch_to_tsquery('english', %s)
        ORDER BY score DESC, p.name ASC, p.id DESC
        LIMIT %s
        """,
        (q, user_id, q, limit),
    )

    rows = cur.fetchall() or []
    out = []
    for r in rows:
        name = (r.get("name") or "").strip()
        category = (r.get("category") or "").strip()
        company = (r.get("company") or "").strip()
        label = name or f"Professional {r['id']}"
        meta = " • ".join([x for x in [category, company] if x])
        if meta:
            label = f"{label} ({meta})"

        out.append({
            "type": "professional",
            "id": r["id"],
            "label": label,
            "snippet": (r.get("snippet") or "").strip(),
            "score": float(r.get("score") or 0),
        })
    return out

def search_transactions(conn, user_id: int, q: str, limit: int = 20):
    q = _normalize_query(q)
    if len(q) < 2:
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            tx.id,
            tx.contact_id,
            tx.transaction_type,
            tx.status,
            tx.address,
            ts_rank(
                setweight(to_tsvector('english', COALESCE(tx.address, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(tx.transaction_type, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(tx.status, '')), 'B'),
                websearch_to_tsquery('english', %s)
            ) AS score,
            left(COALESCE(tx.address, ''), 240) AS snippet
        FROM transactions tx
        WHERE tx.user_id = %s
          AND (
            setweight(to_tsvector('english', COALESCE(tx.address, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(tx.transaction_type, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(tx.status, '')), 'B')
          ) @@ websearch_to_tsquery('english', %s)
        ORDER BY score DESC, tx.id DESC
        LIMIT %s
        """,
        (q, user_id, q, limit),
    )

    rows = cur.fetchall() or []
    out = []
    for r in rows:
        tx_type = (r.get("transaction_type") or "").strip().upper()
        status = (r.get("status") or "").strip()
        address = (r.get("address") or "").strip()
        label = address or f"Transaction {r['id']}"
        if tx_type or status:
            label = f"{label} ({tx_type} {status})".strip()

        out.append({
            "type": "transaction",
            "id": r["id"],
            "contact_id": r.get("contact_id"),
            "label": label,
            "snippet": (r.get("snippet") or "").strip(),
            "score": float(r.get("score") or 0),
        })
    return out

def semantic_broaden(conn, user_id: int, q: str, per_type_limit: int = 10):
    q = _normalize_query(q)
    empty = {"contacts": [], "engagements": [], "transactions": [], "professionals": []}

    if len(q) < 2:
        return empty

    try:
        from services.openai_client import call_embeddings_model
        emb = call_embeddings_model(q)
    except Exception:
        # Never 500 the search page due to AI being unavailable
        return empty

    if not emb:
        return empty

    cur = conn.cursor(cursor_factory=RealDictCursor)

    min_sim = 0.40  # Local Default
    cur.execute(
        """
        SELECT
            object_type,
            object_id,
            contact_id,
            label,
            search_text,
            1 - (embedding <=> %s::vector) AS score
        FROM search_index
        WHERE user_id = %s
          AND (1 - (embedding <=> %s::vector)) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (emb, user_id, emb, min_sim, emb, per_type_limit * 8),
    )

    rows = cur.fetchall() or []
    if not rows:
        return empty

    top_score = float(rows[0].get("score") or 0)
    floor = max(min_sim, top_score - 0.12)
    rows = [r for r in rows if float(r.get("score") or 0) >= floor]

    buckets = {"contacts": [], "engagements": [], "transactions": [], "professionals": []}

    def push(bucket_key, r):
        snippet = (r.get("search_text") or "").strip()
        if len(snippet) > 260:
            snippet = snippet[:260].rstrip() + "…"
        buckets[bucket_key].append({
            "type": bucket_key[:-1],
            "id": r["object_id"],
            "contact_id": r.get("contact_id"),
            "label": (r.get("label") or "").strip() or f"{bucket_key[:-1].title()} {r['object_id']}",
            "snippet": snippet,
            "score": float(r.get("score") or 0),
        })

    for r in rows:
        t = (r.get("object_type") or "").strip().lower()
        if t == "contact" and len(buckets["contacts"]) < per_type_limit:
            push("contacts", r)
        elif t == "engagement" and len(buckets["engagements"]) < per_type_limit:
            push("engagements", r)
        elif t == "transaction" and len(buckets["transactions"]) < per_type_limit:
            push("transactions", r)
        elif t == "professional" and len(buckets["professionals"]) < per_type_limit:
            push("professionals", r)

        if (
            len(buckets["contacts"]) >= per_type_limit and
            len(buckets["engagements"]) >= per_type_limit and
            len(buckets["transactions"]) >= per_type_limit and
            len(buckets["professionals"]) >= per_type_limit
        ):
            break

    return buckets

def search_all(conn, user_id: int, q: str):
    q = _normalize_query(q)
    results = {
        "query": q,
        "contacts": [],
        "engagements": [],
        "transactions": [],
        "professionals": [],
    }

    if len(q) < 2:
        return results

    results["contacts"] = search_contacts(conn, user_id, q, limit=20)
    results["engagements"] = search_engagements(conn, user_id, q, limit=30)
    results["transactions"] = search_transactions(conn, user_id, q, limit=20)
    results["professionals"] = search_professionals(conn, user_id, q, limit=20)

    return results
