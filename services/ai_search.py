# services/ai_search.py

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from psycopg2.extras import RealDictCursor
from typing import Callable, Optional, List, Dict, Any, Tuple

# args: (object_type, object_id, contact_id) -> url


# We intentionally import retrieval from the existing search service
from services.search_service import search_all, semantic_broaden  # tenant-scoped via user_id

# We intentionally reuse your OpenAI client + guard + parsers patterns
# , increment_ai_usage_on_success
from services.openai_client import call_answer_model, is_ai_available
from services.ai_parsers import parse_ai_answer_json

from services.ai_guard import ensure_ai_allowed_and_reset_if_needed, AIGuardError


SUPPORTED_TYPES = ("contacts", "engagements", "transactions", "professionals")

def _snapshot_allows(snap) -> Tuple[bool, str]:
    """
    AIUsageSnapshot contract:
      - allowed if daily_requests_used < daily_request_limit
      - and (if monthly_cap_cents is set) monthly_spend_cents < monthly_cap_cents
    """
    try:
        daily_used = int(snap.daily_requests_used)
        daily_limit = int(snap.daily_request_limit)
        monthly_spend = int(snap.monthly_spend_cents)
        monthly_cap = snap.monthly_cap_cents
        if monthly_cap is not None:
            monthly_cap = int(monthly_cap)

        if daily_used >= daily_limit:
            return False, f"AI daily limit reached ({daily_used}/{daily_limit})."

        if monthly_cap is not None and monthly_spend >= monthly_cap:
            return False, "AI monthly cap reached."

        return True, ""
    except Exception:
        return False, "AI usage not allowed."

@dataclass
class Candidate:
    type: str
    id: int
    label: str
    url: str
    snippet: str
    score: float
    contact_id: Optional[int] = None


def interpret_query(q: str) -> Dict[str, Any]:
    """
    Lightweight interpretation only. Do not call the model.
    Purpose: hints for retrieval limits and confidence heuristics.
    """
    q_norm = (q or "").strip()
    hints = {
        "has_time_language": bool(re.search(r"\b(last year|yesterday|today|this week|last month|in \d{4})\b", q_norm, re.I)),
        "mentions_attorney": bool(re.search(r"\b(attorney|lawyer|counsel)\b", q_norm, re.I)),
        "mentions_client": bool(re.search(r"\b(client|buyer|seller)\b", q_norm, re.I)),
        "mentions_contract": bool(re.search(r"\b(contract|attorney review|agreement)\b", q_norm, re.I)),
        "q_norm": q_norm,
    }
    return hints


def _dedupe_candidates(items: List[Candidate]) -> List[Candidate]:
    seen = set()
    out: List[Candidate] = []
    for c in items:
        key = (c.type, c.id)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _truncate(text: str, max_len: int = 900) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[:max_len].rstrip() + "…"


def _candidates_from_results(results: Dict[str, List[Dict[str, Any]]]) -> List[Candidate]:
    candidates: List[Candidate] = []

    for typ in SUPPORTED_TYPES:
        for r in results.get(typ, []) or []:
            try:
                cid = r.get("contact_id")

                # Build richer evidence text for engagements, because the
                # answer often lives in notes/summary_clean (not just snippet).
                raw_snippet = " ".join(
                    filter(
                        None,
                        [
                            (r.get("label") or "").strip(),
                            (r.get("snippet") or "").strip(),
                        ],
                    )
                )

                candidates.append(
                    Candidate(
                        type=typ[:-1] if typ.endswith("s") else typ,  # "engagements" -> "engagement"
                        id=int(r.get("id")),
                        label=(r.get("label") or "").strip(),
                        url=(r.get("url") or "").strip(),
                        snippet=_truncate(raw_snippet),
                        score=float(r.get("score") or 0.0),
                        contact_id=int(cid) if cid is not None else None,
                    )
                )

            except Exception:
                # Fail safe: ignore malformed row rather than break answer mode.
                continue

    return candidates

def _hydrate_engagement_snippets(conn, user_id: int, candidates: List[Candidate]) -> None:
    """
    For engagement candidates, fetch richer text directly from engagements table.
    This lets Answer Mode see attorney names that are not present in search_index.search_text.
    Mutates candidates in place.
    """
    ids = [c.id for c in candidates if c.type == "engagement"]
    if not ids:
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT
            id,
            summary_clean,
            notes,
            transcript_raw
        FROM engagements
        WHERE user_id = %s
          AND id = ANY(%s::int[])
        """,
        (user_id, ids),
    )
    rows = cur.fetchall() or []
    by_id = {int(r["id"]): r for r in rows}

    for c in candidates:
        if c.type != "engagement":
            continue
        row = by_id.get(int(c.id))
        if not row:
            continue

        rich = " ".join(
            filter(
                None,
                [
                    (row.get("summary_clean") or "").strip(),
                    (row.get("notes") or "").strip(),
                    (row.get("transcript_raw") or "").strip(),
                ],
            )
        ).strip()

        if rich:
            c.snippet = _truncate(rich)

UrlBuilder = Callable[[str, int, Optional[int]], str]

def _apply_urls(candidates: List["Candidate"], url_builder: Optional[UrlBuilder]) -> None:
    """
    Ensure Candidate.url is populated deterministically when a url_builder is provided.
    Safe and fail-closed: never raises.
    """
    if not url_builder:
        return

    for c in candidates:
        try:
            if not (c.url or "").strip():
                c.url = url_builder(c.type, int(c.id), c.contact_id)
            c.url = (c.url or "").strip()
        except Exception:
            c.url = (c.url or "").strip() or ""

def retrieve_candidates(conn, user_id: int, q: str, *, per_type_limit: int = 10, url_builder: Optional[UrlBuilder] = None) -> Dict[str, Any]:
    """
    Retrieval-first and tenant-safe: relies on existing search_all and semantic_broaden.
    """
    interpreted = interpret_query(q)

    base = search_all(conn, user_id, q)  # deterministic
    broad = semantic_broaden(conn, user_id, q, per_type_limit=per_type_limit)  # embeddings (may be empty)

    base_candidates = _candidates_from_results(base)
    broad_candidates = _candidates_from_results(broad or {})

    merged = _dedupe_candidates(base_candidates + broad_candidates)

    # Sort by score descending (FTS scores and semantic scores share the same field name in your output)
    merged.sort(key=lambda c: c.score, reverse=True)

    # Keep payload small and predictable
    top_n = merged[: (per_type_limit * len(SUPPORTED_TYPES))]
    
    _hydrate_engagement_snippets(conn, user_id, top_n)

    _apply_urls(top_n, url_builder)


    return {
        "interpreted": interpreted,
        "counts": {
            "base_total": len(base_candidates),
            "broad_total": len(broad_candidates),
            "merged_total": len(merged),
            "top_n": len(top_n),
        },
        "candidates": top_n,
    }


def _build_llm_payload(query: str, candidates: List[Candidate]) -> Dict[str, Any]:
    """
    Only retrieved content goes into the model. No external knowledge.
    """
    items = []
    for c in candidates:
        items.append(
            {
                "type": c.type,          # e.g. "engagement"
                "id": c.id,              # object id
                "label": c.label,        # human label
                "url": c.url,            # for UI
                "snippet": c.snippet,    # grounded evidence excerpt
                "contact_id": c.contact_id,
                "score": c.score,
            }
        )

    return {
        "query": query,
        "rules": [
            "Use ONLY the provided items. Do not use outside knowledge.",
            "If you cannot answer from items, return no_answer true.",
            "Every answer must include at least one citation referencing an item by type and id.",
            "Never cite an item not present in items.",
            "If multiple plausible answers exist, list up to 3 options, each with citations.",
            "Return STRICT JSON matching the schema.",
        ],
        "schema": {
            "answer": "string (empty allowed if no_answer true)",
            "no_answer": "boolean",
            "citations": [{"type": "string", "id": "number"}],
            "confidence": "number between 0 and 1",
            "notes": "string optional, short warning or clarification",
        },
        "items": items,
    }


def _validate_citations(citations: List[Dict[str, Any]], candidates: List[Candidate]) -> Tuple[bool, List[Dict[str, Any]]]:
    allowed = {(c.type, c.id) for c in candidates}
    cleaned = []
    for c in citations or []:
        try:
            typ = str(c.get("type") or "").strip().lower()
            if typ.endswith("s"):
                typ = typ[:-1]
    
            oid = int(c.get("id"))
            if (typ, oid) in allowed:
                cleaned.append({"type": typ, "id": oid})
        except Exception:
            continue
    
    ok = len(cleaned) > 0
    return ok, cleaned


def compute_confidence(model_conf: float, retrieval_counts: Dict[str, int], citations_ok: bool) -> float:
    """
    Deterministic confidence adjustment.
    """
    conf = float(model_conf or 0.0)
    if not citations_ok:
        return 0.0

    top_n = int(retrieval_counts.get("top_n", 0))
    base_total = int(retrieval_counts.get("base_total", 0))

    # If retrieval is thin, dampen confidence.
    if top_n <= 3:
        conf *= 0.65
    if base_total == 0:
        conf *= 0.75

    # Clamp
    if conf < 0.0:
        conf = 0.0
    if conf > 1.0:
        conf = 1.0
    return conf

def _enrich_citations(
    cleaned: List[Dict[str, Any]],
    candidates: List[Candidate],
    url_builder: Optional[UrlBuilder] = None,
) -> List[Dict[str, Any]]:
    by_key = {(c.type, c.id): c for c in candidates}
    out: List[Dict[str, Any]] = []

    for c in cleaned:
        typ = c["type"]
        oid = c["id"]
        cand = by_key.get((typ, oid))

        if not cand:
            # Citation points to something retrieved but not present in candidates list
            # (should be rare after validation). Keep stable fields.
            url = ""
            if url_builder:
                try:
                    url = (url_builder(typ, int(oid), None) or "").strip()
                except Exception:
                    url = ""
            out.append({
                "type": typ,
                "id": oid,
                "label": f"{typ} #{oid}",
                "url": url,
                "snippet": "",
            })
            continue

        url = (cand.url or "").strip()
        if not url and url_builder:
            try:
                url = (url_builder(cand.type, int(cand.id), cand.contact_id) or "").strip()
            except Exception:
                url = ""

        out.append({
            "type": typ,
            "id": oid,
            "label": cand.label or f"{typ} #{oid}",
            "url": url,
            "snippet": cand.snippet or "",
        })

    return out

def generate_answer(conn, user_id: int, query: str, *, per_type_limit: int = 10, url_builder: Optional[Callable[[str, int, Optional[int]], str]] = None,
) -> Dict[str, Any]:
    """
    Full Answer Mode:
      guard -> retrieve -> if none, no answer
      model call -> strict parse -> validate citations -> return
    """
    q = (query or "").strip()
    if len(q) < 2:
        return {"ok": True, "no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "warning": "Query too short."}

    # AI availability + guard (fail closed)
    if not is_ai_available():
        return {"ok": True, "no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "warning": "AI is unavailable."}

    try:
        snap = ensure_ai_allowed_and_reset_if_needed(conn, user_id)
    except AIGuardError as e:
        return {
            "ok": True,
            "no_answer": True,
            "answer": "",
            "citations": [],
            "confidence": 0.0,
            "warning": e.message,
        }
    
    allowed, guard_msg = _snapshot_allows(snap)
    if not allowed:
        return {
            "ok": True,
            "no_answer": True,
            "answer": "",
            "citations": _enrich_citations(cleaned_citations, candidates, url_builder=url_builder),
            "confidence": 0.0,
            "warning": guard_msg,
        }

    retrieval = retrieve_candidates(conn, user_id, q, per_type_limit=per_type_limit, url_builder=url_builder)
    candidates: List[Candidate] = retrieval["candidates"]

    if not candidates:
        return {"ok": True, "no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "warning": "No relevant data found."}

    payload = _build_llm_payload(q, candidates)

    # Model call: returns text JSON
    raw = call_answer_model(json.dumps(payload))

    parsed = parse_ai_answer_json(raw)  # strict parse, should return dict with keys

    # parsed must contain: no_answer, answer, citations, confidence, notes(optional)
    citations_ok, cleaned_citations = _validate_citations(parsed.get("citations") or [], candidates)

    if parsed.get("no_answer") is True:
        return {"ok": True, "no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "warning": parsed.get("notes") or "No supported answer."}

    if not citations_ok:
        # Enforce “no citations means no answer”
        return {"ok": True, "no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "warning": "Answer rejected because it did not cite retrieved objects."}

    model_conf = float(parsed.get("confidence") or 0.0)
    conf = compute_confidence(model_conf, retrieval["counts"], citations_ok)

    warning = None
    if conf < 0.55:
        warning = parsed.get("notes") or "Low confidence. Please verify."

    # # Increment usage only after success (answer + citations)
    # increment_ai_usage_on_success(conn, user_id)

    return {
        "ok": True,
        "no_answer": False,
        "answer": (parsed.get("answer") or "").strip(),
        "citations": _enrich_citations(cleaned_citations, candidates),
        "confidence": conf,
        "warning": warning,
        "meta": retrieval["counts"],
    }
    
