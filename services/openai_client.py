import os
from dataclasses import dataclass

def is_ai_available() -> bool:
    # Basic availability check for local and prod.
    # If you have a stronger internal flag in this file, use that instead.
    return bool((os.getenv("OPENAI_API_KEY") or "").strip())

class OpenAIUpstreamError(RuntimeError):
    pass


class OpenAITimeoutError(RuntimeError):
    pass


class OpenAIMissingDependencyError(RuntimeError):
    pass


class OpenAIEmbeddingsUnavailableError(Exception):
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


def _get_openai_client(api_key: str):
    """
    Lazy import to prevent app boot failure if openai isn't installed.
    """
    try:
        from openai import OpenAI  # lazy import
    except Exception as e:
        raise OpenAIMissingDependencyError(
            "OpenAI SDK is not installed on this server."
        ) from e

    return OpenAI(api_key=api_key)


def _extract_response_text(resp) -> str:
    # Works across common SDK response shapes
    try:
        # Newer SDKs
        return (resp.output_text or "").strip()
    except Exception:
        pass

    # Try object-like shape
    try:
        out = resp.output
        if out and out[0].content and out[0].content[0].text:
            return str(out[0].content[0].text).strip()
    except Exception:
        pass

    # Try dict-like shape
    try:
        out = resp.get("output") or []
        if out:
            content = out[0].get("content") or []
            if content:
                return str(content[0].get("text") or "").strip()
    except Exception:
        pass

    return ""


def call_responses_api(
    *,
    model: str,
    input_text: str,
    temperature: float = 0.0,
    max_output_tokens: int = 800,
) -> str:
    cfg = get_openai_config()
    client = _get_openai_client(cfg.api_key)

    try:
        resp = client.responses.create(
            model=model,
            input=input_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            timeout=cfg.timeout_seconds,
        )
        text = _extract_response_text(resp)
        if not text:
            raise OpenAIUpstreamError("Empty response from OpenAI")
        return text

    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg:
            raise OpenAITimeoutError("OpenAI request timed out") from e
        if isinstance(e, OpenAIMissingDependencyError):
            raise
        raise OpenAIUpstreamError("OpenAI request failed") from e

def call_summarize_model(*, system_prompt: str, instruction_prompt: str, user_transcript: str) -> str:
    """
    Returns raw text output; caller will parse into structured fields.
    Does not log transcript or raw response.
    """
    cfg = get_openai_config()
    client = _get_openai_client(cfg.api_key)

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
        if isinstance(e, OpenAIMissingDependencyError):
            raise
        raise OpenAIUpstreamError("OpenAI request failed") from e

def call_embeddings_model(text: str):
    text = (text or "").strip()
    if not text:
        return None

    try:
        from openai import OpenAI
    except Exception as e:
        raise OpenAIMissingDependencyError() from e

    client = OpenAI()

    try:
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return resp.data[0].embedding
    except Exception as e:
        raise OpenAIEmbeddingsUnavailableError(str(e)) from e
        
# services/openai_client.py (additions)

def get_answer_model_name() -> str:
    return (
        os.getenv("OPENAI_MODEL_ANSWER", "").strip()
        or os.getenv("OPENAI_MODEL_SUMMARIZE", "").strip()
        or "gpt-4.1-mini"
    )

def call_answer_model(input_text: str) -> str:
    """
    Must return a JSON string (the model output). Keep it minimal and fail safe.
    Implement using the same Responses API pattern as summarization.
    """
    model = get_answer_model_name()
    # Use your existing responses client call here.
    # Example shape (adapt to your existing code):
    resp_text = call_responses_api(
        model=model,
        input_text=input_text,
        temperature=0.0,
        max_output_tokens=700,
    )
    return resp_text

