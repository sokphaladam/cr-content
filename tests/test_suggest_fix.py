import json
from types import SimpleNamespace

from crcontent.quality_preview import SuggestRequest, suggest_fix
from crcontent.script import VideoScript


def test_suggest_fix_keeps_only_real_changes(monkeypatch):
    options = [
        {"scene": 1, "field": "narration", "text": "In 1922, a tomb opened.", "why": "names the year"},
        {"scene": 1, "field": "narration", "text": "Old line.", "why": "no change"},  # same as now: dropped
        {"scene": 9, "field": "on_screen_text", "text": "X", "why": "no such scene"},  # dropped
    ]
    reply = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"options": options}))])
    fake = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=lambda **k: reply)))
    monkeypatch.setattr("crcontent.script.make_client", lambda: fake)
    script = VideoScript.model_validate({"title": "T", "caption": "", "hashtags": [], "scenes": [{"narration": "Old line.", "visual_query": "tomb"}]})
    out = suggest_fix(SuggestRequest(script=script, issue={"title": "The hook names nothing concrete"}))
    assert out == [{"scene": 0, "field": "narration", "text": "In 1922, a tomb opened.", "why": "names the year"}]
