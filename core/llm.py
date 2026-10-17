"""Thin client for the model served on AMD GPUs through AMD Token Factory (AMD Radeon Cloud).

Token Factory exposes an OpenAI-compatible endpoint: POST {AMD_API_BASE}/chat/completions with a
Bearer key. Base URL, key and model name come from environment variables; nothing is hard-coded.
Values used for the demo (from the Token Factory documentation):
    AMD_API_BASE=https://developer.amd.com.cn/radeon/api/v1
    AMD_MODEL=Gemma-4-31B-IT         (instruction-tuned, no "thinking" by default; system message first)

The team key is shared and rate limited (per-minute, concurrency and a daily spend cap), so only
429 and 502/503 responses are retried, with short exponential backoff and jitter. A long wait is
not worth it in a live reply screen: the app falls back to its templates instead.

Quick test once the variables are set:  python -m core.llm
"""
import os
import random
import re
import time

import requests

ENV_KEYS = ("AMD_API_BASE", "AMD_API_KEY", "AMD_MODEL")
RETRY_STATUS = {429, 502, 503}
MAX_RETRIES = 2
MAX_WAIT_S = 4  # longer Retry-After values (60 s per-minute limit) fail fast to the templates
TIMEOUT_S = 15  # a buyer is waiting: past this, try the faster fallback model (Gemma usually answers in 7-10 s)
FALLBACK_TIMEOUT_S = 10
FALLBACK_DEFAULT = "DeepSeek-V4-Flash"  # in the Token Factory catalog, no "thinking" by default


class LLMError(RuntimeError):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def config():
    return {k: os.getenv(k, "").strip() for k in ENV_KEYS}


def is_configured():
    return all(config().values())


def model_name():
    return config()["AMD_MODEL"] or "not configured"


def _error_text(resp):
    """Gateway errors are {"error": {...}}, platform errors {"detail": {"error": {...}}}."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200]
    if not isinstance(body, dict):
        return str(body)[:200]
    detail = body.get("detail")
    err = body.get("error") or (detail.get("error") if isinstance(detail, dict) else detail)
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or err)[:200]
    return str(body)[:200]


def _wait_seconds(resp, attempt):
    try:
        retry_after = float(resp.headers.get("Retry-After", ""))
    except ValueError:
        retry_after = 0.5 * 2 ** attempt
    return retry_after + random.uniform(0, 0.3)


def fallback_model():
    """A faster model on the same AMD endpoint, tried once when the main model is slow or saturated.
    Set AMD_MODEL_FALLBACK to empty to turn it off."""
    return os.getenv("AMD_MODEL_FALLBACK", FALLBACK_DEFAULT).strip()


def _call(cfg, model, messages, max_tokens, temperature, timeout, json_mode):
    url = cfg["AMD_API_BASE"].rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers={"Authorization": f"Bearer {cfg['AMD_API_KEY']}"},
                                 json=payload, timeout=timeout)
        except requests.Timeout as e:
            raise LLMError(f"{model} took longer than {timeout} s.", retryable=True) from e
        except requests.RequestException as e:
            raise LLMError(f"Could not reach the model endpoint ({e.__class__.__name__}).", retryable=True) from e
        if resp.status_code not in RETRY_STATUS or attempt == MAX_RETRIES:
            break
        wait = _wait_seconds(resp, attempt)
        if wait > MAX_WAIT_S:
            break
        time.sleep(wait)

    if resp.status_code != 200:
        raise LLMError(f"{model} returned HTTP {resp.status_code}: {_error_text(resp)}",
                       retryable=resp.status_code == 429 or resp.status_code >= 500)
    try:
        choice = resp.json()["choices"][0]
        text = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected response format from the model endpoint.") from e

    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()  # reasoning models
    if not text:
        raise LLMError(f"Model returned no text (finish_reason: {choice.get('finish_reason')}).")
    return text


def chat(messages, max_tokens=300, temperature=0.4, timeout=TIMEOUT_S, json_mode=False):
    """Returns (text, seconds, model that answered). Raises LLMError with a readable message on failure.

    The main model gets `timeout` seconds. If it times out, is saturated (429/5xx) or unreachable, the
    fallback model on the same AMD endpoint gets one short try before the app uses its templates.
    json_mode asks the endpoint for a JSON object (Token Factory accepts response_format json_object)."""
    cfg = config()
    if not all(cfg.values()):
        raise LLMError("AMD_API_BASE, AMD_API_KEY and AMD_MODEL must be set.")
    start = time.perf_counter()
    model = cfg["AMD_MODEL"]
    try:
        text = _call(cfg, model, messages, max_tokens, temperature, timeout, json_mode)
    except LLMError as e:
        backup = fallback_model()
        if not e.retryable or not backup or backup == model:
            raise
        try:
            text = _call(cfg, backup, messages, max_tokens, temperature, FALLBACK_TIMEOUT_S, json_mode)
        except LLMError as e2:
            raise LLMError(f"{e} Fallback: {e2}") from e2
        model = backup
    return text, time.perf_counter() - start, model


if __name__ == "__main__":
    reply, secs, who = chat([{"role": "user", "content": "Reply with exactly: AMD OK"}], max_tokens=20)
    print(f"{reply!r} in {secs:.1f}s from {who}")
