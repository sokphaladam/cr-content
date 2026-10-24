"""Google Gemini behind the call shape the app already uses for Claude, so the rest of the code barely changes:

    client = make_client()
    response = client.beta.messages.create(model=..., max_tokens=..., system=..., messages=[...],
                                           output_config={"effort": "low", "format": {"type": "json_schema", "schema": S}})
    response.stop_reason        # "end_turn" | "max_tokens" | "refusal"
    response.stop_details       # why, when it was refused
    response.content            # [Block(type="text", text=...)]

Messages may hold text and base64 image blocks. The error classes mirror the ones `web.py` turns into messages.
The key is GEMINI_API_KEY (the app loads .env into the environment); LLM_MODEL picks the model.
"""
import json
import os
import time
from dataclasses import dataclass, field

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# A rolling alias, so it keeps working when Google retires a named model (gemini-2.5-flash already refuses new
# accounts). Live test 2026-10-24: answers in 1-2 s with valid JSON. The regular Flash models gave better-thinking but
# were slow or overloaded that day (up to 179 s, one 503): set LLM_MODEL=gemini-flash-latest in .env to try them.
DEFAULT_MODEL = "gemini-flash-lite-latest"
TIMEOUT = 180
RETRIES = (2.0, 6.0)                # waits before the 2nd and 3rd attempt on 429 / 5xx
_sleep = time.sleep

REFUSED = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY", "RECITATION", "OTHER"}
THINKING_TOKENS = {"low": 0, "medium": 1024, "high": 4096}   # 2.5 Flash family: thinking tokens count against the cap
HEADROOM = {"low": 1024, "medium": 4096, "high": 8192}        # extra cap for other thinking models (not billed unless used)


class APIError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class APIConnectionError(APIError):
    pass


class APIStatusError(APIError):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class BadRequestError(APIStatusError):
    pass


class AuthenticationError(APIStatusError):
    pass


class RateLimitError(APIStatusError):
    pass


@dataclass
class Block:
    type: str
    text: str = ""


@dataclass
class Response:
    content: list[Block] = field(default_factory=list)
    stop_reason: str = "end_turn"
    stop_details: str = ""


def model_name(name: str | None) -> str:
    """The model to call: LLM_MODEL (or the default) when the caller still passes an old Claude name."""
    name = (name or "").strip()
    if not name or name.startswith("claude"):
        return os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODEL
    return name


def _parts(content) -> list[dict]:
    if isinstance(content, str):
        return [{"text": content}]
    parts = []
    for b in content:
        if b.get("type") == "text":
            parts.append({"text": b["text"]})
        elif b.get("type") == "image":
            src = b["source"]
            parts.append({"inlineData": {"mimeType": src["media_type"], "data": src["data"]}})
    return parts


def build_body(max_tokens: int, system: str | None, messages: list[dict], output_config: dict | None,
               model: str, schema_in_body: bool = True) -> dict:
    cfg = output_config or {}
    schema = (cfg.get("format") or {}).get("schema")
    system_text = system or ""
    gen: dict = {"maxOutputTokens": max_tokens}
    if schema is not None:
        gen["responseMimeType"] = "application/json"
        if schema_in_body:
            gen["responseJsonSchema"] = schema
        else:   # a model that rejects the schema field: ask for the shape in words instead
            system_text += "\n\nReply with ONLY a JSON object that follows this JSON schema:\n" + json.dumps(schema)
    effort = cfg.get("effort", "medium")
    if "2.5" in model and "flash" in model and schema_in_body:
        budget = THINKING_TOKENS.get(effort, 1024)
        gen["thinkingConfig"] = {"thinkingBudget": budget}
        gen["maxOutputTokens"] = max_tokens + budget
    elif "lite" not in model and ("flash" in model or "pro" in model):
        # newer thinking models spend the cap on thinking first (a live call came back cut off at 400 tokens)
        gen["maxOutputTokens"] = max_tokens + HEADROOM.get(effort, 4096)
    body = {"contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": _parts(m["content"])}
                         for m in messages],
            "generationConfig": gen}
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}
    return body


def parse_response(data: dict) -> Response:
    block = (data.get("promptFeedback") or {}).get("blockReason")
    cands = data.get("candidates") or []
    if block or not cands:
        return Response(stop_reason="refusal", stop_details=block or "Gemini returned no answer")
    cand = cands[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    finish = cand.get("finishReason", "STOP")
    if finish == "MAX_TOKENS":
        reason = "max_tokens"
    elif finish in REFUSED and not text:
        reason = "refusal"
    else:
        reason = "end_turn"
    return Response([] if reason == "refusal" else [Block("text", text)], reason,
                    finish if reason == "refusal" else "")


def _error(status: int, body: str) -> APIStatusError:
    try:
        msg = json.loads(body)["error"]["message"]
    except (ValueError, KeyError, TypeError):
        msg = body[:300] or f"HTTP {status}"
    if status == 400:
        return BadRequestError(msg, status)
    if status in (401, 403):
        return AuthenticationError(msg, status)
    if status == 429:
        return RateLimitError(msg, status)
    return APIStatusError(msg, status)


class _Messages:
    def __init__(self, client: "Client"):
        self.client = client

    def create(self, *, model: str | None = None, max_tokens: int = 4096, messages: list[dict],
               system: str | None = None, output_config: dict | None = None, **_ignored) -> Response:
        """`betas`, `fallbacks` and other Claude-only arguments are accepted and ignored."""
        name = model_name(model)
        body = build_body(max_tokens, system, messages, output_config, name)
        try:
            return parse_response(self.client.post(name, body))
        except BadRequestError as e:
            if not any(w in e.message.lower() for w in ("schema", "thinking", "responsejson", "unknown name")):
                raise
        # the model refused the schema or thinking fields: once more with the plain request
        return parse_response(self.client.post(name, build_body(max_tokens, system, messages, output_config, name,
                                                                schema_in_body=False)))


class _Beta:
    def __init__(self, client: "Client"):
        self.messages = _Messages(client)


class Client:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.messages = _Messages(self)
        self.beta = _Beta(self)

    def post(self, model: str, body: dict) -> dict:
        if not self.api_key:
            raise AuthenticationError("GEMINI_API_KEY is not set (add it to .env)", 401)
        for attempt in range(len(RETRIES) + 1):
            try:
                r = requests.post(URL.format(model=model), json=body, timeout=TIMEOUT,
                                  headers={"x-goog-api-key": self.api_key})
            except requests.RequestException as e:
                if attempt < len(RETRIES):
                    _sleep(RETRIES[attempt])
                    continue
                raise APIConnectionError(str(e)) from e
            if r.status_code == 429 or r.status_code >= 500:
                if attempt < len(RETRIES):
                    _sleep(RETRIES[attempt])
                    continue
            if r.status_code >= 400:
                raise _error(r.status_code, r.text)
            return r.json()
        raise APIConnectionError("no answer from Gemini")   # unreachable; keeps the type checker calm


def make_client() -> Client:
    return Client()
