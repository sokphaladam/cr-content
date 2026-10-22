"""The pre-flight report, before anything renders: the rule checks, Claude's hook judge, the loop check and a
storyboard (one frame per beat, as the Short frames it, with how its footage was searched). preflight.json holds it
all; preflight.html shows it (it opens from disk; served by the engine it can also apply a suggestion and approve).

The status is honest: "Ready" only when every check passes, the hook judge gives 6/10 or more and every beat's clip
matches its planned shot (7/10 or more); otherwise "Needs work", with the reasons first. Rendering waits for your OK
either way (the approval is longform.storyboard's: any change after it needs approving again).
"""
import copy
import html
import json
import re
import subprocess
from pathlib import Path

from ..longform.storyboard import CSS as STORYBOARD_CSS
from ..visuals import IMAGE_EXTS
from . import match, timing
from .footage import PLACEHOLDERS, placeholders, weak
from .plan import HASHTAG

TERMINAL = re.compile(r"[.!?。]['\"”’)]*$")
JUDGE_READY = 6  # the hook judge's score a Short needs to be called ready


def loop_line(ep, loop: dict) -> dict:
    """Rule 3: the last line ends mid-sentence and runs into the first as one natural sentence (loop: judge.loop)."""
    last = ep.script.scenes[-1].voiceover.strip()
    open_end = bool(last) and not TERMINAL.search(last)
    if not open_end:
        return {"check": "loop line", "ok": False,
                "detail": f"the last line ends a sentence, so the loop doesn't run on: \"…{last[-50:]}\"; end it "
                          "mid-sentence (\"—\")"}
    detail = f"\"{loop['joined']}\""
    if not loop["natural"]:
        detail += f": {loop['problem'] or 'not one natural sentence'}"
    elif loop["by"] != "Claude":
        detail += " (only checked for repeated words: Claude isn't available)"
    if not ep.loop_marked:
        detail += " (no [loops] marker in the sheet)"
    return {"check": "loop line", "ok": loop["natural"], "detail": detail}


def checks(ep, tl, voices, entries: list[dict], cfg: dict, loop: dict) -> list[dict]:
    out = timing.checks(ep.script, tl, voices, cfg)
    out.append(loop_line(ep, loop))
    hook = entries[0]
    looped = hook["chosen"]["source"] not in PLACEHOLDERS
    out.append({"check": "loop shot", "ok": looped,
                "detail": f"the last {cfg['rules']['loop_tail']}s cut back to the opening shot" if looped else
                "the hook is a placeholder: the loop can't return to the opening shot"})
    h = hook["chosen"].get("hook") or {}
    rejected = sum(1 for a in hook["search"]["attempts"] if a["reject"]) if hook.get("search") else 0
    own = hook["chosen"]["source"] == "own"
    hook_ok = looped and not hook["flags"] and ((own and hook.get("match") is None) or (hook.get("match") or 0) >= match.PASS)
    out.append({"check": "hook shot", "ok": hook_ok,
                "detail": ("; ".join(hook["flags"]) or
                           (f"your clip, shot match {hook.get('match') if hook.get('match') is not None else '-'}/10, "
                            f"own motion {h.get('own', 0):.1f}" if own else
                            f"shot match {hook.get('match')}/10, own motion {h.get('own', 0):.1f}, sharp "
                            f"{h.get('sharp', 0):.2f}, from {h.get('start', 0):.1f}s of the clip; {rejected} clips "
                            "rejected"))})
    low = weak(entries)
    out.append({"check": "shot match", "ok": not low,
                "detail": ("every beat's clip shows its planned shot (7/10 or more)" if not low else
                           "; ".join(f"beat {e['scene']} {e.get('match') or 0}/10" for e in entries if e["scene"] in low)
                           + ": add your own clips, or see how each was searched below")})
    tags = HASHTAG.findall(ep.title)
    moved = [n for n in ep.notes if n.startswith("moved #")]
    out.append({"check": "title", "ok": not tags,
                "detail": (f"hashtags in the title: {' '.join('#' + t for t in tags)}" if tags else
                           "no hashtags in the title" + (f" ({moved[0]})" if moved else ""))})
    cards = placeholders(entries)
    out.append({"check": "placeholders", "ok": not cards,
                "detail": f"placeholder cards on beat(s) {', '.join(map(str, cards))}" if cards else
                "every beat shows footage"})
    reused = [f"beat {e['scene']}: {f}" for e in entries for f in e["flags"] if f.startswith("reused:")]
    out.append({"check": "fresh clips", "ok": not reused,
                "detail": "; ".join(reused) if reused else "no clip another Short used in the last 14 days, and a "
                                                            "hook no other Short has used"})
    return out


def status(report: dict) -> dict:
    """{state: ready | needs work | not judged, reasons}."""
    reasons = [f"{c['check']}: {c['detail']}" for c in report["checks"] if not c["ok"]]
    j = report.get("judge")
    if j and j["score"] < JUDGE_READY:
        reasons.insert(0, f"hook judge {j['score']}/10 (needs {JUDGE_READY} or more)")
    state = "needs work" if reasons else "ready" if j else "not judged"
    if not j:
        reasons.append("the hook judge needs Claude (ANTHROPIC_API_KEY in Settings)")
    return {"state": state, "reasons": reasons}


def beat_frames(job: Path, entries: list[dict], tl) -> list[str]:
    """storyboard/beat-XX.jpg: one 9:16 frame per beat, cropped around the animal as the render does."""
    names = []
    for e, slot in zip(entries, tl.slots):
        c = e["chosen"]
        path = Path(c["file"])
        fx, fy = c.get("focus") or (0.5, 0.5)
        crop = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:"
                f"x='min(max(iw*{fx:.3f}-ow/2,0),iw-ow)':y='min(max(ih*{fy:.3f}-oh/2,0),ih-oh)',scale=360:640")
        name = f"beat-{e['scene']:02d}.jpg"
        seek = [] if path.suffix.lower() in IMAGE_EXTS else \
            ["-ss", f"{float(c.get('start', 0.5)) + min(1.0, slot.length / 2):.2f}"]
        subprocess.run(["ffmpeg", "-y", "-v", "error", *seek, "-i", str(path), "-frames:v", "1", "-vf", crop,
                        "-q:v", "3", str(job / "storyboard" / name)], stdin=subprocess.DEVNULL, check=False)
        names.append(name)
    return names


CSS = STORYBOARD_CSS + """
.state { display:inline-block; font-weight:800; font-size:14px; padding:3px 12px; border-radius:99px; margin-right:8px; }
.state.ready { background:var(--ok); color:#fff; } .state.work { background:var(--warn); color:#fff; }
.state.unjudged { background:var(--soft); color:#fff; }
.reasons { margin:8px 0 0; padding-left:20px; color:var(--warn); } .reasons li { margin:3px 0; }
.checks { list-style:none; margin:0; padding:0; }
.checks li { padding:4px 0; display:flex; gap:10px; }
.checks .mark { font-weight:800; width:1.2em; flex:none; }
.checks .ok .mark { color:var(--ok); } .checks .bad .mark { color:var(--warn); }
.checks b { min-width:110px; display:inline-block; }
.big { font-size:34px; font-weight:800; line-height:1; color:var(--accent); }
.sugs { display:grid; grid-template-columns:1fr 1fr; gap:12px 22px; margin-top:12px; }
.sugs ol { margin:6px 0 0; padding-left:20px; } .sugs li { margin:7px 0; }
.sugs .stat { color:var(--soft); font-size:12px; font-variant-numeric:tabular-nums; }
.sugs .long { color:var(--warn); }
button.apply { font-size:12px; padding:2px 10px; margin-left:6px; vertical-align:1px; }
.fix { margin-top:12px; padding:10px 12px; border:1px dashed var(--line); border-radius:10px; }
.beats { display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:14px; }
.beat { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:10px; }
.beat.flagged { border-color:var(--warn); }
.beat img { width:100%; aspect-ratio:9/16; object-fit:cover; border-radius:10px; display:block; background:#000; }
.beat .ontext { font-size:16px; } .beat .vo { font-size:14px; }
.matchscore { font-weight:800; } .matchscore.good { color:var(--ok); } .matchscore.bad { color:var(--warn); }
details.how { margin-top:8px; font-size:12px; color:var(--soft); }
details.how summary { cursor:pointer; color:var(--ink); font-weight:600; }
details.how ol { margin:4px 0 0; padding-left:18px; } details.how li { margin:2px 0; }
details.how a { color:var(--accent); }
.changed { color:var(--accent); font-weight:600; }
.mine { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
.mine label.upload { font:13px "Segoe UI", system-ui, sans-serif; padding:5px 11px; border-radius:8px; cursor:pointer;
  border:1px solid var(--line); background:var(--card); color:var(--ink); }
.mine label.upload.wanted { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:650; }
.mine label.upload.off { opacity:.5; cursor:default; }
.approve { font:14px ui-monospace, Consolas, monospace; background:var(--bg); border:1px solid var(--line);
  border-radius:8px; padding:8px 10px; overflow-wrap:anywhere; }
@media (max-width: 760px) { .sugs { grid-template-columns:1fr; } }
"""

# Live when the engine serves the page (/media/<job>/preflight.html, as the app shows it): Apply changes the Short and
# rebuilds this page; Approve renders it (inside the app, the app follows the render too). From disk, the bar points
# to the command instead.
SCRIPT = r"""
const live = location.protocol.startsWith('http') && location.pathname.startsWith('/media/');
const job = live ? decodeURIComponent(location.pathname.split('/')[2]) : '';
const $ = (sel) => document.querySelector(sel);
const btn = $('#approve'), status = $('#status'), bar = $('#progress');
const state = document.body.dataset.state, reasons = Number(document.body.dataset.reasons || 0);
status.textContent = !live ? 'Opened from disk: render it from the app, or with the command above.'
  : state === 'ready' ? 'Ready. Approve to render the Short, its cover and metadata.'
  : `Needs work: ${reasons} reason(s) at the top. Fix them, or approve to render it anyway.`;
btn.disabled = !live;
document.querySelectorAll('button.apply').forEach((b) => { b.disabled = !live; });
const links = (files) => files.forEach((f, i) => {
  if (i) status.append(' · ');
  const a = document.createElement('a'); a.href = f; a.textContent = f; status.append(a);
});
// rendered already? (the engine's video summary says so without a 404 for a video that isn't made yet)
if (live) fetch(`/api/videos/${encodeURIComponent(job)}`).then((r) => r.ok ? r.json() : null).then((v) => {
  if (!v || !v.video) return;  // not rendered yet
  status.textContent = 'Rendered: '; links(['video.mp4', 'cover.png', 'metadata.txt']);
  btn.textContent = 'Render again';
}).catch(() => {});
document.addEventListener('click', async (e) => {
  const b = e.target.closest('button.apply');
  if (!b || !live) return;
  document.querySelectorAll('button.apply, #approve').forEach((x) => { x.disabled = true; });
  b.textContent = 'Applying…';
  status.textContent = 'Re-voicing beat 1, re-timing and re-running the checks (about half a minute)…';
  try {
    const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/apply`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ field: b.dataset.field, value: b.dataset.value }) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    location.reload();
  } catch (err) {
    status.textContent = 'Apply failed: ' + err.message;
    document.querySelectorAll('button.apply, #approve').forEach((x) => { x.disabled = false; });
    b.textContent = 'Apply';
  }
});
// your own clip for a beat: upload (or replace) it, or remove it to go back to the stock pick; the checks run again
const busyAll = (on) => {
  document.querySelectorAll('button.apply, button.remove, #approve').forEach((x) => { x.disabled = on; });
  document.querySelectorAll('.mine input[type=file]').forEach((x) => { x.disabled = on; x.parentElement.classList.toggle('off', on); });
};
if (!live) busyAll(true);
async function changeClip(beat, method, body, doing) {
  busyAll(true);
  status.textContent = `${doing} for beat ${beat}, then every check runs again (about half a minute)…`;
  try {
    const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/beats/${beat}/clip`, { method, body });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    location.reload();
  } catch (err) { status.textContent = 'That didn\'t work: ' + err.message; busyAll(false); }
}
document.querySelectorAll('.mine input[type=file]').forEach((input) => input.addEventListener('change', () => {
  const file = input.files[0];
  if (!file || !live) return;
  const form = new FormData(); form.append('file', file);
  changeClip(input.dataset.beat, 'POST', form, `Uploading ${file.name}`);
}));
document.querySelectorAll('button.remove').forEach((b) => b.addEventListener('click', () => {
  if (live) changeClip(b.dataset.beat, 'DELETE', null, 'Going back to the stock clip');
}));
btn.addEventListener('click', async () => {
  if (state !== 'ready' && !confirm(`This Short needs work (${reasons} reason(s) at the top). Render anyway?`)) return;
  btn.disabled = true; status.textContent = 'Starting the render…';
  try {
    const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/approve`, { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    if (parent !== window) parent.postMessage({ type: 'storyboard-render', kind: 'short', id: data.id, job }, '*');
    bar.hidden = false;
    const tick = async () => {
      const j = await (await fetch(`/api/jobs/${data.id}`)).json();
      bar.value = Math.max(j.step - 5, 0) + (j.progress || 0); bar.max = 2;
      if (j.status === 'done') {
        bar.hidden = true; status.textContent = 'Done: '; links(['video.mp4', 'cover.png', 'metadata.txt']);
        btn.textContent = 'Render again'; btn.disabled = false;
        return;
      }
      if (j.status === 'error') { bar.hidden = true; btn.disabled = false; status.textContent = 'Render failed: ' + (j.error || ''); return; }
      status.textContent = `Rendering · step ${j.step}/7${j.detail ? ' · ' + j.detail : ''}`;
      setTimeout(tick, 1500);
    };
    tick();
  } catch (err) { btn.disabled = false; status.textContent = err.message; }
});
"""

e = html.escape


def _apply(field: str, value: str) -> str:
    return f"<button class=\"apply\" data-field=\"{field}\" data-value=\"{e(value)}\">Apply</button>"


def _sug(items: list[dict], field: str) -> str:
    out = []
    for it in items:
        stat = (f"{it['style']} · not measured yet" if it.get("stayed") is None else
                f"{it['style']} · stayed {it['stayed']}% · viewed {it['viewed']}% ({it['videos']} videos)")
        said = ""
        if it.get("seconds") is not None:
            said = (f" · <span class=\"{'' if it['fits'] else 'long'}\">spoken in {it['seconds']:.2f}s"
                    f"{'' if it['fits'] else ', over the 2 s'}</span>")
        out.append(f"<li>{e(it['text'])}{_apply(field, it['text'])}<div class=\"stat\">{e(stat)}{said}</div></li>")
    return "".join(out)


def _how(entry: dict) -> str:
    """The beat's search log: the planned shot and its key objects, every query, every clip checked."""
    s = entry.get("search")
    if not s:
        return ""

    def attempts(plan_queries: list[str]) -> str:
        rows = []
        for q in plan_queries:
            mine = [a for a in s["attempts"] if a["query"] == q and not a.get("recent")]
            if not mine:
                rows.append(f"<li><b>{e(q)}</b>: nothing new found</li>")
                continue
            parts = []
            for a in mine:
                what = (f"{a['score']}/10 {e(a['seen'])}" if a["score"] is not None else "")
                if a.get("missing"):
                    what += f" (no {e(', '.join(a['missing']))})"
                if a["reject"]:
                    what = (what + " · " if what else "") + f"rejected: {e(a['reject'])}"
                parts.append(f"<a href=\"{e(a['page'])}\" target=\"_blank\">{e(a['source'])}</a> {what}")
            rows.append(f"<li><b>{e(q)}</b>: " + "; ".join(parts) + "</li>")
        return "<ol>" + "".join(rows) + "</ol>"

    plan = s["plan"]
    body = (f"<div>Planned: {e(plan['shot'])}" + (f" · key objects: {e(', '.join(plan['key_objects']))}"
                                                   if plan["key_objects"] else "") + "</div>"
            + attempts(plan["queries"]))
    if s.get("simpler"):
        sp = s["simpler"]
        body += (f"<div class=\"changed\">Nothing matched, so a simpler shot was tried: {e(sp['shot'])}"
                 + (f" (key objects: {e(', '.join(sp['key_objects']))})" if sp["key_objects"] else "") + "</div>"
                 + attempts(sp["queries"]))
    if s.get("skipped"):
        body += "<div>Not used for the hook (other Shorts use them): " + "; ".join(
            f"<a href=\"{e(k['page'])}\" target=\"_blank\">{e(k['key'])}</a> {e(k['reason'])}" for k in s["skipped"][:6]) + "</div>"
    recent = [a for a in s["attempts"] if a.get("recent")]
    if recent:
        body += "<div>Used lately by other Shorts, tried last: " + "; ".join(
            f"{e(a['key'])} {a['score'] if a['score'] is not None else '-'}/10 ({e(', '.join(a['recent']))})"
            for a in recent) + "</div>"
    n = sum(1 for a in s["attempts"] if a["score"] is not None)
    return f"<details class=\"how\"><summary>How it was searched ({n} clips checked)</summary>{body}</details>"


def page(job: Path, ep, tl, entries: list[dict], report: dict, frames: list[str]) -> str:
    st = report["status"]
    badge = {"ready": ("ready", "Ready"), "needs work": ("work", "Needs work"),
             "not judged": ("unjudged", "Not judged")}[st["state"]]
    reasons = "".join(f"<li>{e(r)}</li>" for r in st["reasons"])
    checks_html = "".join(
        f"<li class=\"{'ok' if c['ok'] else 'bad'}\"><span class=\"mark\">{'✓' if c['ok'] else '!'}</span>"
        f"<span><b>{e(c['check'])}</b> {e(c['detail'])}</span></li>" for c in report["checks"])
    j = report.get("judge")
    if j:
        judge_html = (f"<div class=\"head\"><span class=\"big\">{j['score']}/10</span><span>{e(j['reason'])}</span>"
                      f"</div><div class=\"sugs\"><div><b>Stronger first lines</b><ol>{_sug(j['first_lines'], 'line')}"
                      f"</ol></div><div><b>Stronger on-screen hooks</b><ol>{_sug(j['hook_texts'], 'text')}</ol></div>"
                      f"</div><p class=\"hint\">Ranked by {e(j['ranked_by'])}. Apply changes this Short's beat 1 "
                      "(your spreadsheet stays as it is), re-times it and runs every check again.</p>")
        fix = report.get("hook_fix")
        if fix:
            judge_html += (f"<div class=\"fix\"><b>The hook line runs past 2 s.</b> Shorter: \"{e(fix['text'])}\" "
                           f"(spoken in {fix['seconds']:.2f}s){_apply('line', fix['text'])}"
                           + (f"<div class=\"stat\">The judge on it: {fix['score']}/10. {e(fix['reason'])}</div>"
                              if fix.get("score") is not None else "") + "</div>")
    else:
        judge_html = "<p class=\"hint\">The hook judge needs Claude (ANTHROPIC_API_KEY in Settings).</p>"
    lp = report["loop"]
    loop_html = f"<p>\"{e(lp['joined'])}\"</p>"
    if not lp["natural"]:
        loop_html += f"<p class=\"reasons\">{e(lp['problem'])}</p>"
        if lp.get("fix"):
            loop_html += (f"<div class=\"fix\">A first line that completes it: \"{e(lp['fix'])}\""
                          + (f" (spoken in {lp['fix_seconds']:.2f}s)" if lp.get("fix_seconds") else "")
                          + f"{_apply('line', lp['fix'])}</div>")
    beats = []
    for ent, slot, scene, frame in zip(entries, tl.slots, ep.script.scenes, frames):
        c = ent["chosen"]
        if c["source"] == "own":
            src = "your clip"
        elif c["source"] in PLACEHOLDERS:
            src = "placeholder card"
        else:
            src = f"{c['source']} {c.get('kind', '')}"
        score = ent.get("match")
        badge_html = ("" if score is None else
                      f" · <span class=\"matchscore {'good' if score >= match.PASS else 'bad'}\">shot match {score}/10</span>")
        link = f" · <a href=\"{e(c['page'])}\" target=\"_blank\">source</a>" if c.get("page") else ""
        opening = " · the opening shot again" if ent.get("reuses_opening") else ""
        flags = "".join(f"<div>{e(f)}</div>" for f in ent["flags"])
        flagged = ent["flags"] or (score is not None and score < match.PASS)
        mine = c["source"] == "own"
        tools = (f"<div class=\"mine\"><label class=\"upload{' wanted' if flagged and not mine else ''}\">"
                 f"<input type=\"file\" accept=\"video/*,image/*\" data-beat=\"{scene.n}\" hidden>"
                 f"{'Replace my clip' if mine else 'Upload your clip'}</label>"
                 + (f"<button class=\"remove\" data-beat=\"{scene.n}\">Remove my clip</button>" if mine else "")
                 + "</div>")
        beats.append(
            f"<div class=\"beat{' flagged' if flagged else ''}\"><img src=\"storyboard/{frame}\" alt=\"\">"
            f"<div class=\"head\"><span class=\"n\">{scene.n}</span><span class=\"time\">{slot.start:.1f}–"
            f"{slot.end:.1f}s</span></div><div class=\"ontext\">{e(scene.text)}</div>"
            f"<div class=\"vo\">{e(scene.voiceover)}</div><div class=\"visual\">{e(scene.visual)}</div>"
            f"<div class=\"src\">{e(src)}{badge_html}{opening}{link}</div>"
            + (f"<div class=\"flags\">{flags}</div>" if flags else "") + tools + _how(ent) + "</div>")
    changes = [n for n in ep.notes if n.startswith(("First line changed", "On-screen hook changed"))]
    changes_html = ("<div class=\"panel\"><h2>Changed here</h2><ul>" + "".join(f"<li>{e(c)}</li>" for c in changes)
                    + "</ul><p class=\"hint\">Your spreadsheet still has the old text: copy these into it.</p></div>"
                    ) if changes else ""
    skipped = report.get("sources_skipped") or []
    return f"""<!doctype html>
<html lang="{ep.script.lang}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pre-flight · Ep {ep.ep}</title><style>{CSS}</style></head>
<body data-state="{st['state']}" data-reasons="{len(st['reasons'])}"><main>
<h1>{e(ep.title)}</h1>
<p class="meta"><span class="state {badge[0]}">{badge[1]}</span>Ep {ep.ep} · {len(ep.script.scenes)} beats ·
 {tl.total:.1f}s from the real voiceover · {ep.animal and e(ep.animal.split(':')[0])}</p>
{f'<ul class="reasons">{reasons}</ul>' if reasons else ''}
{changes_html}
<div class="panel"><h2>Checks</h2><ul class="checks">{checks_html}</ul>
{''.join(f'<p class="hint">Not searched: {e(s)}.</p>' for s in skipped)}</div>
<div class="panel"><h2>Hook judge</h2>{judge_html}</div>
<div class="panel"><h2>Loop: the last line into the first</h2>{loop_html}</div>
<div class="panel"><h2>Storyboard</h2><div class="beats">{''.join(beats)}</div>
<p class="hint">Press <b>Upload your clip</b> on a beat to use your own video or photo; files you put in
 {e(report['media'])}\\scene-XX.mp4 are picked up when the episode is built again.</p></div>
<div class="panel"><h2>Render</h2><p>When it looks right, press <b>Approve and render</b> below, or from a terminal:</p>
<div class="approve">python make.py --approve "{e(str(job))}"</div></div>
</main>
<div class="bar"><div><span class="status" id="status"></span><progress id="progress" hidden></progress>
<button class="primary" id="approve">Approve and render</button></div></div>
<script>{SCRIPT}</script>
</body></html>"""


def write(job: Path, ep, tl, voices, entries: list[dict], cfg: dict, media: Path, log=print) -> dict:
    """preflight.json and preflight.html; returns the report."""
    from . import judge
    from .footage import sources

    hook_max = float(cfg["rules"]["hook_max"])
    report = {"media": str(media), "sources_skipped": sources(cfg)[1], "loop": judge.loop(ep, log)}
    if report["loop"].get("fix"):
        report["loop"]["fix_seconds"] = judge.measure([{"text": report["loop"]["fix"]}], ep.script.lang, cfg,
                                                      hook_max)[0]["seconds"]
    report["checks"] = checks(ep, tl, voices, entries, cfg, report["loop"])
    j = judge.judge(ep, entries, tl, log)
    if j:
        judge.measure(j["first_lines"], ep.script.lang, cfg, hook_max)
        # the hook line runs long: the best suggestion that fits, judged as if it were the first line
        if not next(c for c in report["checks"] if c["check"] == "hook beat")["ok"]:
            fits = [it for it in j["first_lines"] if it.get("fits")]
            if fits:
                trial = copy.deepcopy(ep)
                trial.script.scenes[0].voiceover = fits[0]["text"]
                again = judge.judge(trial, entries, tl, log)
                report["hook_fix"] = {"text": fits[0]["text"], "seconds": fits[0]["seconds"],
                                      "score": again["score"] if again else None,
                                      "reason": again["reason"] if again else ""}
    report["judge"] = j
    report["status"] = status(report)
    for c in report["checks"]:
        log(f"      {'ok' if c['ok'] else '! '} {c['check']}: {c['detail']}")
    if j:
        log(f"      hook judge: {j['score']}/10")
    log(f"      status: {report['status']['state'].upper()}"
        + "".join(f"\n        - {r}" for r in report["status"]["reasons"]))
    frames = beat_frames(job, entries, tl)
    (job / "preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "preflight.html").write_text(page(job, ep, tl, entries, report, frames), encoding="utf-8")
    return report
