"""The Smart Highlights report: one self-contained HTML page (next to report.json) to compare the candidates.

The song's timeline (sections, the combined score curve, where each candidate sits), then one card per candidate in
final order: timecodes, score breakdown, Claude's reason, hook text, caption, lyrics, covers and the rendered clip.
It opens straight from disk (file://); covers and clips are linked by relative paths.
"""
import html
import os
from pathlib import Path

PARTS = [("structure", "Structure"), ("lyrics", "Lyrics"), ("visual", "Visual"), ("hook", "Hook")]
KIND_COLOURS = {"chorus": "var(--chorus)", "hook": "var(--chorus)", "drop": "var(--chorus)",
                "post-chorus": "var(--chorus)", "pre-chorus": "var(--pre)", "bridge": "var(--bridge)",
                "verse": "var(--verse)"}

CSS = """
:root { --bg:#f6f5f2; --card:#ffffff; --ink:#1d1d1f; --soft:#6b6b70; --line:#e4e2dc; --accent:#d9480f;
  --chorus:#f08c00; --pre:#fcc419; --verse:#91a7ff; --bridge:#b197fc; --other:#ced4da; --bar:#1d1d1f; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#131316; --card:#1c1c20; --ink:#ececf0;
  --soft:#9a9aa3; --line:#2c2c33; --accent:#ff8a4c; --verse:#5c7cfa; --bridge:#9775fa; --other:#3a3a42; --bar:#ececf0; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 "Segoe UI", system-ui, sans-serif; }
main { max-width:1100px; margin:0 auto; padding:28px 16px 64px; }
h1 { font-size:28px; margin:0 0 4px; letter-spacing:-0.01em; }
.meta { color:var(--soft); margin:0 0 22px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin-bottom:18px; }
.panel h2 { font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--soft); margin:0 0 10px; }
.timeline { position:relative; height:86px; }
.timeline svg { position:absolute; inset:0; width:100%; height:100%; }
.legend { display:flex; gap:14px; flex-wrap:wrap; color:var(--soft); font-size:12px; margin-top:8px; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:18px;
  display:grid; grid-template-columns: 1fr 300px; gap:20px; }
.card.chosen { border-color:var(--accent); box-shadow:0 0 0 1px var(--accent); }
.head { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; }
.rank { font-size:30px; font-weight:800; color:var(--accent); line-height:1; }
.time { font-size:18px; font-weight:650; font-variant-numeric:tabular-nums; }
.tag { font-size:12px; padding:2px 8px; border-radius:99px; background:var(--bg); border:1px solid var(--line); color:var(--soft); }
.score { margin-left:auto; font-size:13px; color:var(--soft); }
.score b { font-size:20px; color:var(--ink); }
.bars { display:grid; grid-template-columns: 74px 1fr 40px; gap:5px 10px; align-items:center; margin:14px 0; font-size:13px; }
.track { height:8px; background:var(--bg); border-radius:99px; overflow:hidden; border:1px solid var(--line); }
.fill { height:100%; background:var(--bar); border-radius:99px; }
.num { text-align:right; font-variant-numeric:tabular-nums; color:var(--soft); }
.reason { margin:10px 0; }
.label { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--soft); margin:12px 0 3px; }
.hooktext { font-size:20px; font-weight:750; }
.caption { white-space:pre-wrap; background:var(--bg); border:1px solid var(--line); border-radius:8px; padding:8px 10px;
  font-size:14px; position:relative; }
.copy { position:absolute; top:6px; right:6px; font:12px inherit; padding:2px 8px; border-radius:6px;
  border:1px solid var(--line); background:var(--card); color:var(--ink); cursor:pointer; }
ol.lyrics { margin:4px 0 0; padding-left:20px; color:var(--soft); font-size:14px; }
ol.lyrics li:first-child { color:var(--ink); font-weight:600; }
.side video { width:100%; border-radius:10px; background:#000; aspect-ratio:9/16; }
.covers { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin-top:8px; }
.covers a { display:block; } .covers img { width:100%; border-radius:6px; display:block; aspect-ratio:9/16; object-fit:cover; }
.covers span { display:block; font-size:11px; color:var(--soft); text-align:center; }
.nopick { color:var(--soft); font-size:13px; }
@media (max-width: 760px) { .card { grid-template-columns:1fr; } .score { margin-left:0; } }
"""

SCRIPT = """
document.querySelectorAll('.copy').forEach(b => b.addEventListener('click', () => {
  const t = b.parentElement.querySelector('span').innerText;
  navigator.clipboard.writeText(t).then(() => { b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy', 1200); });
}));
"""


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def _e(text) -> str:
    return html.escape(str(text or ""))


def _timeline(data: dict) -> str:
    total = max(data["duration"], 1.0)
    w, h = 1000, 86
    parts = []
    for s in data["sections"]:
        x, x2 = s["start"] / total * w, s["end"] / total * w
        colour = KIND_COLOURS.get(s["kind"], "var(--other)")
        parts.append(f'<rect x="{x:.1f}" y="58" width="{max(0.5, x2 - x - 1):.1f}" height="14" rx="3" fill="{colour}">'
                     f'<title>{_e(s["name"])} {_clock(s["start"])}–{_clock(s["end"])}</title></rect>')
    # the combined per-second score (the weights' mix of the curves), as a line over the sections
    curves = data["curve"]
    weights = {k: v for k, v in data["weights"].items() if k in curves}
    n = len(next(iter(curves.values())))
    total_w = sum(weights.values()) or 1
    combined = [sum(curves[k][t] * wt for k, wt in weights.items()) / total_w for t in range(n)]
    top = max(combined) or 1
    pts = " ".join(f"{(t + 0.5) / total * w:.1f},{52 - v / top * 44:.1f}" for t, v in enumerate(combined))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="var(--soft)" stroke-width="1.5"/>')
    for e in data["candidates"]:
        x, x2 = e["start"] / total * w, e["end"] / total * w
        chosen = e["candidate"] in data["chosen"]
        parts.append(f'<rect x="{x:.1f}" y="4" width="{x2 - x:.1f}" height="50" rx="4" fill="var(--accent)" '
                     f'fill-opacity="{0.22 if chosen else 0.08}" stroke="var(--accent)" stroke-opacity="{1 if chosen else 0.4}"/>'
                     f'<text x="{x + 4:.1f}" y="18" font-size="13" font-weight="700" fill="var(--accent)">#{e["final_rank"]}</text>')
    for k in range(0, int(total) - 12, 30):  # none in the last seconds: it would be cut off at the edge
        parts.append(f'<text x="{k / total * w:.1f}" y="84" font-size="10" fill="var(--soft)">{_clock(k)[:-3]}</text>')
    return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">{"".join(parts)}</svg>'


def _card(e: dict, data: dict, out: Path) -> str:
    chosen = e["candidate"] in data["chosen"]
    bars = "".join(
        f'<span>{label}</span><div class="track"><div class="fill" style="width:{e["parts"].get(key, 0) * 100:.0f}%">'
        f'</div></div><span class="num">{e["parts"].get(key, 0):.2f}</span>'
        for key, label in PARTS if key in e["parts"])
    ai = e.get("ai") or {}
    reason = (f'<div class="label">Claude\'s reason</div><div class="reason">{_e(ai["reason"])}</div>' if ai else
              f'<div class="reason nopick">Ranked by score (the AI judge was off or unavailable).</div>')
    hook = f'<div class="label">On-screen hook</div><div class="hooktext">{_e(e["hook_text"])}</div>' if ai else ""
    caption = (f'<div class="label">Caption</div><div class="caption"><span>{_e(e["caption"])}</span>'
               f'<button class="copy" type="button">Copy</button></div>') if e.get("caption") else ""
    lyrics = "".join(f"<li>{_e(line)}</li>" for line in e["lyrics"])
    covers = "".join(
        f'<a href="{_e(c["file"])}" target="_blank"><img src="{_e(c["file"])}" alt="Cover at {c["at"]:.1f}s" loading="lazy">'
        f'<span>{c["at"]:.1f}s · {c["score"]:.2f}</span></a>' for c in e["covers"])
    if e.get("video"):
        try:
            rel = os.path.relpath(e["video"], out).replace("\\", "/")
        except ValueError:  # on another drive than the report (Windows): link it absolutely
            rel = Path(e["video"]).as_uri()
        poster = f' poster="{_e(e["covers"][0]["file"])}"' if e["covers"] else ""
        media = f'<video src="{_e(rel)}" controls preload="metadata"{poster}></video>'
    else:
        media = '<p class="nopick">Not rendered (only the top picks are).</p>'
    snap = f'starts on a {e["starts_on"]}, ends on a {e["ends_on"]}'
    order = f'score rank {e["score_rank"]}' + (f' · Claude rank {ai["rank"]}' if ai else "")
    if e["parts"].get("repeat_penalty"):
        order += f' · −{e["parts"]["repeat_penalty"] * 100:.0f}% in the score for sharing lyrics with a higher-scoring pick'
    return f"""
<article class="card{' chosen' if chosen else ''}">
  <div>
    <div class="head"><span class="rank">#{e['final_rank']}</span>
      <span class="time">{_clock(e['start'])} – {_clock(e['end'])}</span>
      <span class="tag">{e['length']:.1f}s</span><span class="tag">{_e(e['section'] or e['kind'])}</span>
      <span class="score">score <b>{e['score']:.3f}</b></span></div>
    <div class="meta" style="margin:4px 0 0">{_e(order)} · {_e(snap)}</div>
    <div class="bars">{bars}</div>
    {reason}{hook}{caption}
    <div class="label">Lyrics</div><ol class="lyrics">{lyrics}</ol>
    <div class="label">Covers</div><div class="covers">{covers}</div>
  </div>
  <div class="side">{media}</div>
</article>"""


def write(data: dict, out: Path) -> Path:
    who = f" — {_e(data['artist'])}" if data.get("artist") else ""
    methods = " · ".join(x for x in (f"structure: {data['structure_method']}", f"lyrics: {data['timing']}",
                                     f"visual: {data['visual_method'] or 'off'}",
                                     f"AI judge: {'Claude' if data['judge'] else 'off'}") if x)
    weights = ", ".join(f"{k} {v}" for k, v in data["weights"].items())
    legend = "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in
                     (("Chorus", "var(--chorus)"), ("Pre-chorus", "var(--pre)"), ("Verse", "var(--verse)"),
                      ("Bridge", "var(--bridge)"), ("Intro / outro / other", "var(--other)")))
    cards = "".join(_card(e, data, out) for e in data["candidates"])
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Highlights · {_e(data['title'])}</title><style>{CSS}</style></head>
<body><main>
<h1>{_e(data['title'])}{who}</h1>
<p class="meta">{_clock(data['duration'])} · {len(data['candidates'])} candidates, top {len(data['chosen'])} rendered · {_e(methods)}<br>
weights: {_e(weights)} (highlights.json)</p>
<section class="panel"><h2>Song timeline</h2><div class="timeline">{_timeline(data)}</div>
<div class="legend">{legend}<span><i style="background:var(--soft)"></i>combined score</span>
<span><i style="background:var(--accent)"></i>candidates (rendered ones outlined)</span></div></section>
{cards}
</main><script>{SCRIPT}</script></body></html>
"""
    path = out / "report.html"
    path.write_text(page, encoding="utf-8")
    return path
