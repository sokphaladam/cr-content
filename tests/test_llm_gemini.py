import json

import pytest
import requests

from crcontent import llm


class Resp:
    def __init__(self, status=200, body=None, text=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.text = text if text is not None else json.dumps(self._body)

    def json(self):
        return self._body


def ok(text="{}", finish="STOP", thought=None):
    parts = ([{"text": thought, "thought": True}] if thought else []) + [{"text": text}]
    return Resp(200, {"candidates": [{"content": {"parts": parts}, "finishReason": finish}]})


SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm, "_sleep", lambda s: None)
    monkeypatch.setattr(llm, "_usage_file", None)


@pytest.fixture(autouse=True)
def usage_file(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "_usage_file", tmp_path / "usage.json")


@pytest.fixture
def client():
    return llm.Client(api_key="k")


def test_request_shape_text_image_schema_and_roles(client, monkeypatch):
    seen = {}
    monkeypatch.setattr("requests.post", lambda url, **kw: seen.update(url=url, **kw) or ok('{"a": "x"}'))
    r = client.beta.messages.create(
        model="gemini-2.5-flash", max_tokens=3000, betas=["x"], fallbacks="default", system="SYS",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [{"type": "text", "text": "hi"},
                                               {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "QUJD"}}]},
                  {"role": "assistant", "content": "earlier"}, {"role": "user", "content": "again"}])
    body = seen["json"]
    assert seen["url"].endswith("/models/gemini-2.5-flash:generateContent") and seen["headers"]["x-goog-api-key"] == "k"
    assert body["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert body["contents"][0]["parts"] == [{"text": "hi"}, {"inlineData": {"mimeType": "image/jpeg", "data": "QUJD"}}]
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
    gen = body["generationConfig"]
    assert gen["responseMimeType"] == "application/json" and gen["responseJsonSchema"] == SCHEMA
    assert gen["thinkingConfig"] == {"thinkingBudget": 0} and gen["maxOutputTokens"] == 3000
    assert r.stop_reason == "end_turn" and next(b.text for b in r.content if b.type == "text") == '{"a": "x"}'


def test_thinking_budget_adds_headroom_only_for_25_flash(client, monkeypatch):
    seen = []
    monkeypatch.setattr("requests.post", lambda url, **kw: seen.append(kw["json"]["generationConfig"]) or ok())
    msg = [{"role": "user", "content": "x"}]
    client.messages.create(model="gemini-2.5-flash", max_tokens=1000, messages=msg, output_config={"effort": "medium"})
    client.messages.create(model="gemini-3.8-flash", max_tokens=1000, messages=msg, output_config={"effort": "medium"})
    client.messages.create(model="gemini-flash-lite-latest", max_tokens=1000, messages=msg, output_config={"effort": "medium"})
    assert seen[0]["maxOutputTokens"] == 2024 and seen[0]["thinkingConfig"]["thinkingBudget"] == 1024
    assert seen[1]["maxOutputTokens"] == 5096 and "thinkingConfig" not in seen[1]   # newer thinking model: headroom only
    assert seen[2]["maxOutputTokens"] == 1000 and "thinkingConfig" not in seen[2]   # lite models don't think by default


def test_claude_model_names_are_remapped(client, monkeypatch):
    urls = []
    monkeypatch.setattr("requests.post", lambda url, **kw: urls.append(url) or ok())
    monkeypatch.delenv("LLM_MODEL", raising=False)
    client.messages.create(model="claude-opus-5-5", messages=[{"role": "user", "content": "x"}])
    monkeypatch.setenv("LLM_MODEL", "gemini-custom")
    client.messages.create(model="claude-opus-5-5", messages=[{"role": "user", "content": "x"}])
    assert llm.DEFAULT_MODEL in urls[0] and "gemini-custom" in urls[1]


def test_stop_reasons_and_thought_parts(client, monkeypatch):
    msg = [{"role": "user", "content": "x"}]
    monkeypatch.setattr("requests.post", lambda url, **kw: ok("answer", thought="thinking out loud"))
    r = client.messages.create(messages=msg)
    assert [b.text for b in r.content] == ["answer"]

    monkeypatch.setattr("requests.post", lambda url, **kw: ok("cut", finish="MAX_TOKENS"))
    assert client.messages.create(messages=msg).stop_reason == "max_tokens"

    blocked = Resp(200, {"promptFeedback": {"blockReason": "SAFETY"}})
    monkeypatch.setattr("requests.post", lambda url, **kw: blocked)
    r = client.messages.create(messages=msg)
    assert r.stop_reason == "refusal" and r.stop_details == "SAFETY" and r.content == []

    empty = Resp(200, {"candidates": [{"finishReason": "SAFETY"}]})
    monkeypatch.setattr("requests.post", lambda url, **kw: empty)
    assert client.messages.create(messages=msg).stop_reason == "refusal"


@pytest.mark.parametrize("status,cls", [(400, llm.BadRequestError), (401, llm.AuthenticationError),
                                        (403, llm.AuthenticationError), (404, llm.APIStatusError)])
def test_http_errors_map_to_the_classes_web_py_expects(client, monkeypatch, status, cls):
    err = Resp(status, text=json.dumps({"error": {"message": "nope"}}))
    monkeypatch.setattr("requests.post", lambda url, **kw: err)
    with pytest.raises(cls) as e:
        client.messages.create(messages=[{"role": "user", "content": "x"}])
    assert e.value.message == "nope" and e.value.status_code == status and isinstance(e.value, llm.APIError)


def test_retries_then_succeeds_and_gives_up(client, monkeypatch):
    answers = [Resp(503, text="busy"), Resp(429, text="slow down"), ok("fine")]
    monkeypatch.setattr("requests.post", lambda url, **kw: answers.pop(0))
    assert client.messages.create(messages=[{"role": "user", "content": "x"}]).content[0].text == "fine"

    monkeypatch.setattr("requests.post", lambda url, **kw: Resp(429, text="slow down"))
    with pytest.raises(llm.RateLimitError):
        client.messages.create(messages=[{"role": "user", "content": "x"}])

    def down(url, **kw):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr("requests.post", down)
    with pytest.raises(llm.APIConnectionError):
        client.messages.create(messages=[{"role": "user", "content": "x"}])


def test_schema_rejected_retries_with_schema_in_the_prompt(client, monkeypatch):
    bodies = []

    def post(url, **kw):
        bodies.append(kw["json"])
        if len(bodies) == 1:
            return Resp(400, text=json.dumps({"error": {"message": "Invalid JSON payload: responseJsonSchema unknown"}}))
        return ok('{"a": "y"}')
    monkeypatch.setattr("requests.post", post)
    r = client.messages.create(model="gemini-2.5-flash", system="SYS", messages=[{"role": "user", "content": "x"}],
                               output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
    assert len(bodies) == 2 and "responseJsonSchema" not in bodies[1]["generationConfig"]
    assert "JSON schema" in bodies[1]["systemInstruction"]["parts"][0]["text"] and r.content[0].text == '{"a": "y"}'


def test_other_bad_requests_are_not_retried(client, monkeypatch):
    calls = []
    monkeypatch.setattr("requests.post", lambda url, **kw: calls.append(1) or Resp(400, text=json.dumps({"error": {"message": "API key not valid"}})))
    with pytest.raises(llm.BadRequestError):
        client.messages.create(messages=[{"role": "user", "content": "x"}])
    assert len(calls) == 1


def test_missing_key_is_an_authentication_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(llm.AuthenticationError, match="GEMINI_API_KEY"):
        llm.make_client().messages.create(messages=[{"role": "user", "content": "x"}])


DAILY = json.dumps({"error": {"message": "Quota exceeded for metric: generate_content_free_tier_requests, limit: 500, "
                              "model: gemini-3.5-flash-lite. Generate content requests per day limit exceeded on "
                              "Free Tier. Please retry in 10h6m38.68s."}})


def test_usage_counts_requests_and_keeps_the_daily_block(client, monkeypatch):
    calls = []
    answers = [ok("{}"), Resp(429, text=DAILY)]
    monkeypatch.setattr("requests.post", lambda url, **kw: calls.append(1) or answers.pop(0))
    client.messages.create(model="m", messages=[{"role": "user", "content": "hi"}])
    with pytest.raises(llm.RateLimitError):
        client.messages.create(model="m", messages=[{"role": "user", "content": "hi"}])
    assert len(calls) == 2   # a daily limit is not retried: retries would only spend more of it
    row = llm.usage()["models"][0]
    assert row["model"] == "m" and row["requests"] == 2 and row["limit"] == 500
    assert 10 * 3600 < row["blocked_for"] <= 10 * 3600 + 400


def test_usage_starts_again_on_a_new_pacific_day():
    t = 1_800_000_000.0
    llm.record("m", 200, now=t)
    day, left = llm._pacific_day(t)
    assert llm.usage(now=t)["models"][0]["requests"] == 1
    assert llm.usage(now=t + left + 1)["models"] == [] and llm.usage(now=t + left + 1)["day"] != day
