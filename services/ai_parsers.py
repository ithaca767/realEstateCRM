import re
import json

from dataclasses import dataclass
from typing import List, Dict, Optional


ONE_SENTENCE_HEADER = "ONE-SENTENCE SUMMARY:"
CRM_NARRATIVE_HEADER = "CRM NARRATIVE SUMMARY:"
FOLLOW_UP_HEADER = "SUGGESTED FOLLOW-UP ITEMS:"


class AIParseError(ValueError):
    """Raised when AI output does not match the required contract."""


def _normalize_text(s: str) -> str:
    # Normalize line endings and trim outer whitespace
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    # Collapse trailing spaces per line
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    return s


def _find_header_positions(text: str) -> Dict[str, int]:
    """
    Find the starting index of each header. Headers must match exactly.
    Returns mapping header -> index in text.
    """
    positions: Dict[str, int] = {}
    for header in (ONE_SENTENCE_HEADER, CRM_NARRATIVE_HEADER, FOLLOW_UP_HEADER):
        idx = text.find(header)
        if idx == -1:
            raise AIParseError(f"Missing required header: {header}")
        positions[header] = idx
    return positions


def _extract_section(text: str, start_header: str, end_header: Optional[str]) -> str:
    """
    Extract section body that begins after start_header and ends before end_header (if provided).
    """
    start_idx = text.find(start_header)
    if start_idx == -1:
        raise AIParseError(f"Missing required header: {start_header}")

    body_start = start_idx + len(start_header)
    if end_header is None:
        body = text[body_start:]
    else:
        end_idx = text.find(end_header)
        if end_idx == -1:
            raise AIParseError(f"Missing required header: {end_header}")
        body = text[body_start:end_idx]

    return body.strip()


def _parse_follow_up_items(section_text: str) -> List[str]:
    """
    Parses the follow-up section.
    Expected:
      - bullet lines starting with '-' (preferred), or
      - the exact phrase 'None identified.' (case-insensitive tolerated)
    We keep this strict but practical.
    """
    raw = section_text.strip()
    if not raw:
        # Contract expects either bullets or "None identified."
        raise AIParseError("Follow-up section is empty.")

    # Accept "None identified." (and minor punctuation variation)
    if re.fullmatch(r"(?i)none identified\.?", raw):
        return []

    items: List[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("-"):
            item = line[1:].strip()
            if item:
                items.append(item)
            continue

        # If the model violated the contract (no '-' bullets), fail
        raise AIParseError("Follow-up items must be bullet lines starting with '-' or 'None identified.'")

    if not items:
        raise AIParseError("No valid follow-up bullet items found.")
    return items


def parse_engagement_summary_output(raw_output: str) -> Dict[str, object]:
    """
    Parse the model's raw output into structured fields.

    Returns:
      {
        "one_sentence_summary": str,
        "crm_narrative_summary": str,
        "suggested_follow_up_items": list[str],
      }

    Raises:
      AIParseError if headers are missing, out of order, or content is invalid.
    """
    text = _normalize_text(raw_output)
    if not text:
        raise AIParseError("AI output is empty.")

    pos = _find_header_positions(text)

    # Enforce header ordering (must be in this exact order)
    if not (pos[ONE_SENTENCE_HEADER] < pos[CRM_NARRATIVE_HEADER] < pos[FOLLOW_UP_HEADER]):
        raise AIParseError("Headers are present but not in the required order.")

    one_sentence = _extract_section(text, ONE_SENTENCE_HEADER, CRM_NARRATIVE_HEADER)
    crm_narrative = _extract_section(text, CRM_NARRATIVE_HEADER, FOLLOW_UP_HEADER)
    follow_up_raw = _extract_section(text, FOLLOW_UP_HEADER, None)

    # Basic content validation
    if not one_sentence:
        raise AIParseError("One-sentence summary is empty.")
    if "\n" in one_sentence.strip():
        # We allow a wrapped line if the model adds it, but we prefer a single sentence.
        # Keep it strict: require it to be one paragraph (no blank lines).
        if "\n\n" in one_sentence:
            raise AIParseError("One-sentence summary must be a single paragraph.")
        # If it is line-wrapped, normalize to a single line
        one_sentence = " ".join(part.strip() for part in one_sentence.split("\n") if part.strip())

    if not crm_narrative:
        raise AIParseError("CRM narrative summary is empty.")

    follow_up_items = _parse_follow_up_items(follow_up_raw)

    return {
        "one_sentence_summary": one_sentence.strip(),
        "crm_narrative_summary": crm_narrative.strip(),
        "suggested_follow_up_items": follow_up_items,
    }

# services/ai_parsers.py (additions)

def parse_ai_answer_json(raw_text: str) -> dict:
    """
    Strict parse. Fail closed.
    Expected keys: no_answer(bool), answer(str), citations(list), confidence(float), notes(optional)
    """
    try:
        data = json.loads((raw_text or "").strip())
    except Exception:
        return {"no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "notes": "Invalid AI response."}

    no_answer = bool(data.get("no_answer"))
    answer = (data.get("answer") or "").strip()
    citations = data.get("citations") or []
    confidence = data.get("confidence")

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    notes = (data.get("notes") or "").strip() if isinstance(data.get("notes"), str) else ""

    if no_answer:
        return {"no_answer": True, "answer": "", "citations": [], "confidence": 0.0, "notes": notes or "No answer."}

    if not isinstance(citations, list):
        citations = []

    return {
        "no_answer": False,
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "notes": notes,
    }
