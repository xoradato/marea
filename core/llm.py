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


class LLMError(RuntimeError):
    pass


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


def chat(messages, max_tokens=400, temperature=0.4, timeout=30, json_mode=False):
    """Returns (text, seconds). Raises LLMError with a readable message on any failure.
    json_mode asks the endpoint for a JSON object (Token Factory accepts response_format json_object)."""
    cfg = config()
    if not all(cfg.values()):
        raise LLMError("AMD_API_BASE, AMD_API_KEY and AMD_MODEL must be set.")

    url = cfg["AMD_API_BASE"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["AMD_MODEL"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    start = time.perf_counter()
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {cfg['AMD_API_KEY']}"},
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as e:
            raise LLMError(f"Could not reach the model endpoint ({e.__class__.__name__}).") from e
        if resp.status_code not in RETRY_STATUS or attempt == MAX_RETRIES:
            break
        wait = _wait_seconds(resp, attempt)
        if wait > MAX_WAIT_S:
            break
        time.sleep(wait)

    if resp.status_code != 200:
        raise LLMError(f"Model endpoint returned HTTP {resp.status_code}: {_error_text(resp)}")
    try:
        choice = resp.json()["choices"][0]
        text = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected response format from the model endpoint.") from e

    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()  # reasoning models
    if not text:
        raise LLMError(f"Model returned no text (finish_reason: {choice.get('finish_reason')}).")
    return text, time.perf_counter() - start


if __name__ == "__main__":
    reply, secs = chat([{"role": "user", "content": "Reply with exactly: AMD OK"}], max_tokens=20)
    print(f"{reply!r} in {secs:.1f}s from {model_name()}")
