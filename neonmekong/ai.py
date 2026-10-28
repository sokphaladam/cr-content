"""Optional AI wording for the upload text. Default is "template": no AI, no cost, handled in uploadtext.py.

  local   Ollama on this PC (http://localhost:11434); pull a small model first: ollama pull qwen2.5:7b-instruct
  gemini  Google Gemini (Flash-Lite has a free tier). GEMINI_API_KEY (and optionally GEMINI_MODEL) come from the
          project's .env file, never from a system environment variable. One small call per song.

The AI writes only two things, the one-line hook and the pinned-comment question; title, tags, description and
lyrics always come from the templates. Every result is cached in songs/<slug>/ai_cache.json and never requested again
unless you pass --refresh. Dry-run never calls anything: it returns a marked mock.
"""
import json
import re
from pathlib import Path

from . import config, songjson

LOCAL_MODEL = "qwen2.5:7b-instruct"
GEMINI_MODEL = "gemini-flash-lite-latest"   # rolling alias; live test 2026-10-24: 1-2 s, valid JSON
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TOKENS = 500
KEYS = ("hook", "pinned_comment")


def prompt(data: dict, chorus_lines: list[str]) -> str:
    return (
        f"You write YouTube upload text for the music channel {config.CHANNEL}.\n"
        f"Song: {data['title']} | genre: {data['genre']} | mood: {data['mood_phrase']} | "
        f"scene: {data['scene_theme']} | style prompt: {data['style_prompt']}\n"
        f"Chorus: {' / '.join(chorus_lines[:4])}\n"
        "Return ONLY a JSON object with these keys:\n"
        '  "hook": one sentence (max 120 characters) that says what the listener will feel\n'
        '  "pinned_comment": one friendly question for viewers (max 150 characters)\n'
        "Do not name real artists."
    )


def parse_reply(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    obj = json.loads(m.group(0) if m else text)
    return {k: " ".join(str(obj[k]).split()) for k in KEYS if obj.get(k)}


def _call_local(text: str, model: str | None = None) -> str:
    import requests
    r = requests.post("http://localhost:11434/api/generate", timeout=300,
                      json={"model": model or LOCAL_MODEL, "prompt": text, "stream": False, "format": "json",
                            "options": {"num_predict": MAX_TOKENS}})
    r.raise_for_status()
    return r.json()["response"]


def _call_gemini(text: str, model: str | None = None) -> str:
    import requests
    from dotenv import dotenv_values
    env = dotenv_values(config.ROOT / ".env")   # the project's .env only: system variables are never read
    key = (env.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set in the project's .env file")
    name = model or (env.get("GEMINI_MODEL") or "").strip() or GEMINI_MODEL
    r = requests.post(GEMINI_URL.format(model=name), timeout=120, headers={"x-goog-api-key": key},
                      json={"contents": [{"role": "user", "parts": [{"text": text}]}],
                            "generationConfig": {"maxOutputTokens": MAX_TOKENS, "temperature": 0.8,
                                                 "responseMimeType": "application/json"}})
    r.raise_for_status()
    body = r.json()
    parts = ((body.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    reply = "".join(p.get("text", "") for p in parts)
    if not reply:
        why = (body.get("promptFeedback") or {}).get("blockReason") or (body.get("candidates") or [{}])[0].get("finishReason")
        raise RuntimeError(f"Gemini returned no text ({why})")
    return reply


BACKENDS = {"local": _call_local, "gemini": _call_gemini}


def generate(folder: Path, data: dict, chorus_lines: list[str], mode: str, refresh: bool = False,
             model: str | None = None, log=print) -> dict:
    """AI wording for `mode` (local / gemini); {} for template mode. Cached per mode in ai_cache.json."""
    if mode == "template":
        return {}
    if mode not in BACKENDS:
        raise ValueError(f"unknown --ai mode {mode!r} (template, local, gemini)")
    if config.dry_run():
        log(f"      dry-run: --ai {mode} not called, using a mock")
        return {"hook": f"[mock] {data['mood_phrase']} for the first replay.",
                "pinned_comment": "[mock] Which line got stuck in your head?"}
    path = folder / "ai_cache.json"
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if mode in cache and not refresh:
        log(f"      --ai {mode}: using ai_cache.json (pass --refresh to ask again)")
        return cache[mode]
    reply = parse_reply(BACKENDS[mode](prompt(data, chorus_lines), model))
    songjson.backup(path)
    path.write_text(json.dumps({**cache, mode: reply}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return reply
