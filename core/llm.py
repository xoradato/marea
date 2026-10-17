"""Thin client for the model served on AMD (Token Factory).

ASSUMPTION, NOT VERIFIED YET: Token Factory exposes an OpenAI-compatible
chat completions endpoint. Check the official user manual and adjust the URL
and payload below if it differs. Base URL, key and model name come from
environment variables; nothing is hard-coded.

Quick test once the variables are set:  python -m core.llm
"""
import os
import re
import time

import requests

ENV_KEYS = ("AMD_API_BASE", "AMD_API_KEY", "AMD_MODEL")


class LLMError(RuntimeError):
    pass


def config():
    return {k: os.getenv(k, "").strip() for k in ENV_KEYS}


def is_configured():
    return all(config().values())


def model_name():
    return config()["AMD_MODEL"] or "not configured"


def chat(messages, max_tokens=400, temperature=0.4, timeout=30):
    """Returns (text, seconds). Raises LLMError with a readable message on any failure."""
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
    start = time.perf_counter()
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {cfg['AMD_API_KEY']}"},
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise LLMError(f"Could not reach the model endpoint ({e.__class__.__name__}).") from e
    if resp.status_code != 200:
        raise LLMError(f"Model endpoint returned HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        text = resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected response format from the model endpoint.") from e

    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()  # reasoning models
    return text, time.perf_counter() - start


if __name__ == "__main__":
    reply, secs = chat([{"role": "user", "content": "Reply with exactly: AMD OK"}], max_tokens=20)
    print(f"{reply!r} in {secs:.1f}s from {model_name()}")
