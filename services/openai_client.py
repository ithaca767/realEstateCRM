import os
from dataclasses import dataclass

from openai import OpenAI


class OpenAIUpstreamError(RuntimeError):
    pass


class OpenAITimeoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model_summarize: str
    timeout_seconds: int


def get_openai_config() -> OpenAIConfig:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = (os.getenv("OPENAI_MODEL_SUMMARIZE") or "gpt-4.1-mini").strip()
    timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS") or "30")

    return OpenAIConfig(
        api_key=api_key,
        model_summarize=model,
        timeout_seconds=timeout_seconds,
    )


def is_ai_globally_available() -> bool:
    raw = (os.getenv("AI_FEATURES_AVAILABLE") or "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def call_summarize_model(*, system_prompt: str, instruction_prompt: str, user_transcript: str) -> str:
    """
    Returns raw text output; caller will parse into structured fields.
    Does not log transcript or raw response.
    """
    cfg = get_openai_config()
    client = OpenAI(api_key=cfg.api_key)

    transcript = (user_transcript or "").strip()
    if not transcript:
        raise ValueError("user_transcript is empty")
    if len(transcript) > 25_000:
        raise ValueError("user_transcript exceeds max length")

    try:
        resp = client.responses.create(
            model=cfg.model_summarize,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": instruction_prompt},
                {"role": "user", "content": f"[BEGIN USER TRANSCRIPT]\n{transcript}\n[END USER TRANSCRIPT]"},
            ],
            timeout=cfg.timeout_seconds,
        )
        text = (resp.output_text or "").strip()
        if not text:
            raise OpenAIUpstreamError("Empty response from OpenAI")
        return text

    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg:
            raise OpenAITimeoutError("OpenAI request timed out") from e
        raise OpenAIUpstreamError("OpenAI request failed") from e
