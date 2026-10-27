"""The pre-flight report, before anything renders: the rule checks, Gemini's hook judge, the loop check and a
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
from urllib.parse import quote

from ..longform.storyboard import CSS as STORYBOARD_CSS
from ..longform.voice import recording
from ..render import duration
from ..visuals import IMAGE_EXTS
from . import edit, match, timing
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
    elif loop["by"] != "Gemini":
        detail += " (only checked for repeated words: Gemini isn't available)"
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
        reasons.append("the hook judge needs Gemini (GEMINI_API_KEY in Settings)")
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
.trim { margin-top:8px; padding:8px; border:1px dashed var(--line); border-radius:10px; }
.trim video { width:100%; aspect-ratio:9/16; object-fit:cover; border-radius:8px; background:#000; display:block; }
.trim input[type=range] { width:100%; margin:4px 0 0; }
.trim .rl { display:flex; justify-content:space-between; font-size:12px; color:var(--soft); margin-top:8px; }
.trim .span { position:relative; height:8px; border-radius:4px; background:var(--line); margin-top:8px; }
.trim .span i { position:absolute; top:0; bottom:0; border-radius:4px; background:var(--accent); }
.trim .read { font-size:12px; color:var(--soft); font-variant-numeric:tabular-nums; }
.trim .result { font-size:13px; margin-top:6px; } .trim .result.bad { color:var(--warn); }
.trim .row { display:flex; gap:6px; flex-wrap:wrap; margin-top:6px; }
.meter { position:relative; height:8px; border-radius:4px; background:var(--line); margin:8px 0 4px; }
.meter i { position:absolute; left:0; top:0; bottom:0; border-radius:4px; background:var(--warn); }
.meter.good i { background:var(--ok); }
.meter b { position:absolute; top:-3px; bottom:-3px; width:2px; background:var(--soft); opacity:.7; }
.chips { display:flex; flex-wrap:wrap; gap:4px; margin-top:4px; }
.chip { font-size:12px; padding:2px 8px; border-radius:99px; border:1px solid var(--line); color:var(--soft); }
.chip.seen { border-color:var(--ok); color:var(--ok); } .chip.miss { border-color:var(--warn); color:var(--warn); }
.chip.extra { opacity:.7; }
.edit { display:grid; grid-template-columns:repeat(3, 1fr) minmax(150px, 190px); gap:10px; align-items:start; }
.edit label { display:block; font-size:12px; color:var(--soft); }
.edit select, .edit button { width:100%; margin-top:4px; font:inherit; padding:6px; border-radius:8px;
  border:1px solid var(--line); background:var(--card); color:var(--ink); }
.edit img { width:100%; aspect-ratio:9/16; object-fit:cover; border-radius:10px; background:#000; grid-row:1 / span 8; grid-column:4; }
.edit .tl { grid-column:1 / span 3; display:flex; gap:3px; }
.edit .tl button { width:auto; min-width:0; margin:0; padding:8px 0; font-size:12px; font-variant-numeric:tabular-nums; }
.edit .tl button.on { border-color:var(--accent); color:var(--accent); font-weight:700; }
.edit .tl button.own { background:color-mix(in srgb, var(--accent) 18%, var(--card)); }
.edit .tune { grid-column:1 / span 3; display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; align-items:end; }
.edit .tune input[type=range] { width:100%; margin-top:6px; }
.edit .tune output { color:var(--ink); font-variant-numeric:tabular-nums; }
.edit label.check { display:flex; align-items:center; gap:6px; color:var(--ink); font-size:14px; }
.edit .narr { grid-column:1 / span 3; display:grid; grid-template-columns:1fr 1.4fr; gap:10px; align-items:end; }
.edit .narr button.setvoice { grid-column:1 / span 2; background:var(--accent); border-color:var(--accent); color:#fff; font-weight:650; }
.edit .vrow { display:flex; gap:6px; align-items:center; }
.edit .vrow select { flex:1; }
.edit .vrow button.listen { width:40px; flex:none; }
.edit .speeds { display:flex; margin-top:4px; border:1px solid var(--line); border-radius:8px; overflow:hidden; }
.edit .speeds button { margin:0; border:0; border-radius:0; background:transparent; color:var(--soft); font-weight:600; white-space:nowrap; }
.edit .speeds button.on { background:var(--line); color:var(--ink); }
.voicebox audio { width:100%; height:32px; }
.voicebox button.rec.on { background:var(--warn); border-color:var(--warn); color:#fff; }
.edit .beatpick { grid-column:1 / span 3; }
.edit .why { grid-column:1 / span 3; margin:0; padding-left:18px; font-size:13px; color:var(--soft); }
.edit .why:empty { display:none; }
.edit button.suggestedit { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:650; }
.edit .gfx { grid-column:1 / span 3; display:flex; flex-wrap:wrap; gap:6px 14px; font-size:14px; }
.edit .gfx b { font-size:12px; color:var(--soft); width:100%; font-weight:600; }
.edit .gfx label { display:flex; align-items:center; gap:6px; font-size:14px; color:var(--ink); }
@media (max-width: 760px) { .edit { grid-template-columns:1fr; } .edit img { grid-row:auto; grid-column:auto; max-width:220px; }
  .edit .beatpick, .edit .tl, .edit .tune, .edit .narr { grid-column:auto; } .edit .tune { grid-template-columns:1fr 1fr; } }
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
  document.querySelectorAll('button.apply, button.remove, button.trimopen, button.trimcheck, button.trimuse, button.rec, button.voiceremove, button.setvoice, #approve').forEach((x) => { x.disabled = on; });
  document.querySelectorAll('.mine input[type=file]').forEach((x) => { x.disabled = on; x.parentElement.classList.toggle('off', on); });
};
if (!live) busyAll(true);
async function changeClip(beat, method, body, doing, what = 'clip') {
  busyAll(true);
  status.textContent = `${doing} for beat ${beat}, then every check runs again (about half a minute)…`;
  try {
    const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/beats/${beat}/${what}`, { method, body });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    location.reload();
  } catch (err) { status.textContent = 'That didn\'t work: ' + err.message; busyAll(false); }
}
document.querySelectorAll('.mine input[type=file]').forEach((input) => input.addEventListener('change', () => {
  const file = input.files[0];
  if (!file || !live) return;
  const form = new FormData(); form.append('file', file);
  const voice = input.classList.contains('voicefile');
  changeClip(input.dataset.beat, 'POST', form, `Uploading ${file.name}`, voice ? 'voice' : 'clip');
}));
// your own voice on a beat: record it here (press again to stop) or upload it; "Use the narrator" puts the TTS back
let recorder = null;
document.querySelectorAll('button.rec').forEach((b) => b.addEventListener('click', async () => {
  if (!live) return;
  if (recorder) { if (recorder.button === b) recorder.stop(); return; }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch (err) { status.textContent = 'No microphone: ' + err.message; return; }
  const parts = [];
  recorder = new MediaRecorder(stream); recorder.button = b;
  recorder.ondataavailable = (ev) => parts.push(ev.data);
  recorder.onstop = () => {
    stream.getTracks().forEach((t) => t.stop());
    recorder = null; b.classList.remove('on'); b.textContent = '● Record voice';
    const form = new FormData(); form.append('file', new Blob(parts, { type: 'audio/webm' }), 'voice.webm');
    changeClip(b.dataset.beat, 'POST', form, 'Saving your voice', 'voice');
  };
  recorder.start(); b.classList.add('on'); b.textContent = '■ Stop';
  const line = b.closest('.beat').querySelector('.vo').textContent;
  status.textContent = `Recording beat ${b.dataset.beat}: read "${line}", then press Stop.`;
}));
document.querySelectorAll('button.voiceremove').forEach((b) => b.addEventListener('click', () => {
  if (live) changeClip(b.dataset.beat, 'DELETE', null, 'Going back to the narrator', 'voice');
}));
// the judge's score as a bar (ticks at the cap for a clip without the key objects, and at the pass mark) and the key
// objects it looked for: green = seen, red = missing, grey = other things in frame
const meterEl = (score, pass, cap) => {
  const m = document.createElement('div'); m.className = 'meter' + (score >= pass ? ' good' : '');
  const fill = document.createElement('i'); fill.style.width = score * 10 + '%'; m.append(fill);
  [cap, pass].forEach((t) => { const b = document.createElement('b'); b.style.left = t * 10 + '%'; m.append(b); });
  return m;
};
const chipsEl = (wanted, missing, seen) => {
  const box = document.createElement('div'); box.className = 'chips';
  const add = (text, cls) => { const c = document.createElement('span'); c.className = 'chip ' + cls; c.textContent = text; box.append(c); };
  (wanted || []).forEach((o) => (missing || []).includes(o) ? add('\u2717 ' + o, 'miss') : add('\u2713 ' + o, 'seen'));
  (seen || []).filter((o) => !(wanted || []).some((w) => w.toLowerCase() === o.toLowerCase())).slice(0, 6).forEach((o) => add(o, 'extra'));
  return box;
};
// edit panel: mood, caption look and cut style; the frame shows the grade and captions as the render will
const editBox = $('.edit');
if (editBox) {
  const gfx = () => [...editBox.querySelectorAll('input[name=gfx]:checked')].map((x) => x.value);
  const sel = (n) => editBox.querySelector('select[name=' + n + ']'), pic = editBox.querySelector('img'), note = $('#editnote');
  const inp = (n) => editBox.querySelector('input[name=' + n + ']');
  // per-beat overrides ({beat: {look, transition}}): the two "this beat" menus show and set the previewed beat's
  const beats = JSON.parse(editBox.dataset.beats || '{}');
  const segs = editBox.querySelectorAll('.tl button');
  const showBeat = () => {
    const n = sel('beat').value, o = beats[n] || {};
    sel('blook').value = o.look || ''; sel('bcut').value = o.transition || '';
    sel('bcut').disabled = n === '1';  // nothing cuts into the opening beat
    segs.forEach((s) => { s.classList.toggle('on', s.dataset.beat === n); s.classList.toggle('own', !!beats[s.dataset.beat]); });
  };
  const keepBeat = () => {
    const o = {};
    if (sel('blook').value) o.look = sel('blook').value;
    if (sel('bcut').value) o.transition = sel('bcut').value;
    if (Object.keys(o).length) beats[sel('beat').value] = o; else delete beats[sel('beat').value];
    showBeat();
  };
  segs.forEach((s) => s.addEventListener('click', () => {
    sel('beat').value = s.dataset.beat; showBeat(); frame();
    const card = document.getElementById('beat-' + s.dataset.beat);
    if (card) card.animate([{ outline: '2px solid var(--accent)' }, { outline: '2px solid transparent' }], 1200);
  }));
  ['blook', 'bcut'].forEach((n) => sel(n).addEventListener('change', () => { keepBeat(); frame(); }));
  ['caption_size', 'caption_y', 'music_volume'].forEach((n) => {
    inp(n).addEventListener('input', () => { inp(n).previousElementSibling.textContent = Number(inp(n).value).toFixed(2); });
    if (n !== 'music_volume') inp(n).addEventListener('change', () => frame());
  });
  const frame = () => {
    const look = (beats[sel('beat').value] || {}).look || sel('look').value;
    const q = new URLSearchParams({ beat: sel('beat').value, look, caption: sel('caption').value, graphics: gfx().join(','),
      size: inp('caption_size').value, y: inp('caption_y').value });
    note.textContent = live ? 'Drawing the frame...' : 'Open this page from the app to preview the edit.';
    if (live) {
      pic.onload = () => { note.textContent = ''; };
      pic.onerror = () => { note.textContent = 'No preview for this beat.'; };
      pic.src = `/api/shorts/${encodeURIComponent(job)}/edit/preview?${q}`;
    }
  };
  ['look', 'caption'].forEach((n) => sel(n).addEventListener('change', frame));
  sel('beat').addEventListener('change', () => { showBeat(); frame(); });
  editBox.querySelectorAll('input[name=gfx]').forEach((x) => x.addEventListener('change', frame));
  // fill the panel in with what suits this Short (the preview shows it; Save edit keeps it)
  editBox.querySelector('button.suggestedit').addEventListener('click', async () => {
    if (!live) return;
    note.textContent = 'Reading the script and its pace…';
    const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/edit/suggest`, { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { note.textContent = data.detail || `HTTP ${r.status}`; return; }
    sel('look').value = data.look; sel('caption').value = data.caption; sel('transition').value = data.transition;
    editBox.querySelectorAll('input[name=gfx]').forEach((x) => { x.checked = data.graphics.includes(x.value); });
    $('#editwhy').innerHTML = '';
    Object.values(data.reasons).forEach((text) => { const li = document.createElement('li'); li.textContent = text; $('#editwhy').append(li); });
    note.textContent = `Suggested: ${data.summary}. Press Save edit to keep it.`;
    frame();
  });
  editBox.querySelector('button.saveedit').addEventListener('click', async () => {
    if (!live) return;
    note.textContent = 'Saving...';
    const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/edit`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ look: sel('look').value, caption: sel('caption').value, transition: sel('transition').value, graphics: gfx(),
        beats, caption_size: Number(inp('caption_size').value), caption_y: Number(inp('caption_y').value),
        music_volume: Number(inp('music_volume').value), push: inp('push').checked }) });
    const data = await r.json().catch(() => ({}));
    note.textContent = r.ok ? 'Saved. Approve to render with it.' : (data.detail || `HTTP ${r.status}`);
  });
  // the narrator: voice + speed as in the app's picker; ▶ plays the first line, a change offers to voice it again
  const narr = editBox.querySelector('.narr'), setBtn = narr.querySelector('button.setvoice');
  const listen = narr.querySelector('button.listen'), player = new Audio();
  let rate = narr.dataset.rate;
  const changed = () => { setBtn.hidden = sel('voice').value === narr.dataset.voice && rate === narr.dataset.rate; };
  narr.querySelectorAll('.speeds button').forEach((b) => b.addEventListener('click', () => {
    rate = b.dataset.rate;
    narr.querySelectorAll('.speeds button').forEach((x) => x.classList.toggle('on', x === b));
    changed();
  }));
  sel('voice').addEventListener('change', changed);
  player.onended = player.onpause = () => { listen.textContent = '▶'; };
  listen.addEventListener('click', async () => {
    if (!live) return;
    if (!player.paused) { player.pause(); return; }
    listen.textContent = '…';
    try {
      const r = await fetch('/api/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: narr.dataset.sample, voice: sel('voice').value, rate }) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
      player.src = URL.createObjectURL(await r.blob());
      await player.play(); listen.textContent = '■';
    } catch (err) { listen.textContent = '▶'; note.textContent = 'No preview: ' + err.message; }
  });
  setBtn.addEventListener('click', async () => {
    if (!live) return;
    busyAll(true);
    status.textContent = 'Voicing every beat with the new voice, then every check runs again (about a minute)…';
    try {
      const r = await fetch(`/api/shorts/${encodeURIComponent(job)}/voice`, { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ voice: sel('voice').value, rate }) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      location.reload();
    } catch (err) { status.textContent = 'That didn\'t work: ' + err.message; busyAll(false); }
  });
  showBeat();
  frame();
}
// trim: pick where the beat's clip starts and where it ends (the beat's length is the voice's, so a stretch longer or
// shorter than that plays faster or slower to fit: 0.5x to 2x), play it, score it, keep it
document.querySelectorAll('.trim').forEach((box) => {
  const beat = box.dataset.beat, len = Number(box.dataset.length), dur = Number(box.dataset.dur);
  const lo = len * 0.5, hi = len * 2;
  const v = box.querySelector('video'), rs = box.querySelector('input.rs'), re = box.querySelector('input.re');
  const read = box.querySelector('.read'), out = box.querySelector('.result'), bar = box.querySelector('.span i');
  const num = (x) => Number(x.value);
  const speed = () => (num(re) - num(rs)) / len;
  // keep the stretch between half and twice the beat, inside the clip: moving one end pushes the other when it must
  const fix = (moved) => {
    let s = num(rs), e = num(re);
    if (moved === 's') { s = Math.min(s, dur - lo); e = Math.min(Math.max(e, s + lo), s + hi, dur); }
    else { e = Math.max(e, lo); s = Math.max(Math.min(s, e - lo), e - hi, 0); }
    rs.value = s.toFixed(2); re.value = e.toFixed(2);
  };
  const show = () => {
    const s = num(rs), e = num(re), x = speed();
    bar.style.left = (s / dur * 100) + '%'; bar.style.width = ((e - s) / dur * 100) + '%';
    const how = Math.abs(x - 1) < 0.02 ? 'normal speed' : (x > 1 ? `${x.toFixed(2)}x faster` : `${x.toFixed(2)}x slow motion`);
    read.textContent = `${s.toFixed(2)}s → ${e.toFixed(2)}s of ${dur.toFixed(1)}s · ${(e - s).toFixed(2)}s shown in the ${len.toFixed(2)}s beat · ${how}`;
    v.playbackRate = Math.min(Math.max(x, 0.5), 2);
  };
  const play = () => { show(); out.textContent = ''; v.currentTime = num(rs); v.play().catch(() => {}); };
  rs.addEventListener('input', () => { fix('s'); play(); });
  re.addEventListener('input', () => { fix('e'); show(); v.currentTime = Math.max(num(re) - Math.min(1, num(re) - num(rs)), num(rs)); v.play().catch(() => {}); });
  v.addEventListener('timeupdate', () => { if (v.currentTime >= num(re)) v.currentTime = num(rs); });
  box.closest('.beat').querySelector('button.trimopen').addEventListener('click', () => {
    box.hidden = !box.hidden;
    if (box.hidden) v.pause(); else { if (!v.src) v.src = v.dataset.src; fix('s'); show(); v.currentTime = num(rs); v.play().catch(() => {}); }
  });
  const send = async (apply) => {
    busyAll(true); out.className = 'result'; out.textContent = apply ? 'Keeping it and running every check again…' : 'Scoring this stretch…';
    try {
      const res = await fetch(`/api/shorts/${encodeURIComponent(job)}/beats/${beat}/trim`, { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ start: num(rs), end: num(re), apply }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      if (apply) { location.reload(); return; }
      const bits = [data.score === null ? 'not scored (Gemini unavailable)' : `shot match ${data.score}/10`];
      if (data.seen) bits.push(data.seen);
      if (data.problem) bits.push(data.problem);
      if (data.reject) bits.push('hook rule: ' + data.reject);
      out.textContent = '';
      if (data.score !== null) out.append(meterEl(data.score, data.pass, data.cap));
      out.append(bits.join(' · '));
      if (data.score !== null) out.append(chipsEl(data.key_objects, data.missing, data.objects_seen));
      out.classList.toggle('bad', (data.score !== null && data.score < Number(box.dataset.pass)) || !!data.reject);
    } catch (err) { out.textContent = 'That did not work: ' + err.message; out.classList.add('bad'); }
    busyAll(false);
  };
  box.querySelector('button.trimcheck').addEventListener('click', () => live && send(false));
  box.querySelector('button.trimuse').addEventListener('click', () => live && send(true));
});
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


def _objects_html(ent: dict) -> str:
    """The judge's verdict on a beat: a 0-10 bar (ticks at the cap and the pass mark) and its key objects, seen or
    missing; "" when the beat wasn't judged."""
    score = ent.get("match")
    if score is None:
        return ""
    c = ent["chosen"]
    plan = (ent.get("search") or {}).get("plan") or {}
    wanted, missing = plan.get("key_objects", []), c.get("missing", [])
    chips = [f"<span class=\"chip {'miss' if o in missing else 'seen'}\">{'✗' if o in missing else '✓'} {e(o)}</span>"
             for o in wanted]
    wanted_l = {o.lower() for o in wanted}
    chips += [f"<span class=\"chip extra\">{e(o)}</span>" for o in c.get("objects_seen", [])[:6]
              if o.lower() not in wanted_l]
    return (f"<div class=\"meter{' good' if score >= match.PASS else ''}\" title=\"shot match {score}/10\">"
            f"<i style=\"width:{score * 10}%\"></i><b style=\"left:{match.GENERIC_MAX * 10}%\"></b>"
            f"<b style=\"left:{match.PASS * 10}%\"></b></div>"
            + (f"<div class=\"chips\">{''.join(chips)}</div>" if chips else ""))


def _edit_html(entries: list[dict], choice: dict, lang: str, tl, job: Path, sample: str) -> str:
    """The Edit panel: a timeline of the beats, mood, caption look and cut style for the Short and per beat, the
    fine-tune sliders and the narrator, with a frame preview."""
    def select(name: str, options: dict, current: str) -> str:
        return (f"<select name=\"{name}\">" + "".join(
            f"<option value=\"{e(k)}\"{' selected' if k == current else ''}>{e(v)}</option>"
            for k, v in options.items()) + "</select>")

    def slider(name: str, label: str, value: float, step: float) -> str:
        lo, hi = edit.NUMBERS[name]
        return (f"<label>{label} <output>{value:.2f}</output><input type=\"range\" name=\"{name}\" min=\"{lo}\" "
                f"max=\"{hi}\" step=\"{step}\" value=\"{value:.2f}\"></label>")

    from . import RATES, graphics, narrator, settings, voices_for

    opts = edit.options()
    voice, rate = narrator(job, lang)
    speeds = "".join(f"<button type=\"button\" data-rate=\"{k}\" class=\"{'on' if k == rate else ''}\">{v}</button>"
                     for k, v in RATES.items())
    beat = select("beat", {str(x["scene"]): f"Beat {x['scene']}" for x in entries}, "1")
    timeline = "".join(f"<button class=\"seg{' own' if str(s.scene) in choice['beats'] else ''}\" data-beat=\"{s.scene}\" "
                       f"style=\"flex:{s.length:.2f}\" title=\"Beat {s.scene}: {s.length:.1f}s\">{s.scene}</button>"
                       for s in tl.slots)
    same = {"": "Same as the Short"}
    music = choice["music_volume"] if choice["music_volume"] is not None else float(settings.load()["music"]["volume"])
    gfx = "".join(f"<label><input type=\"checkbox\" name=\"gfx\" value=\"{k}\"{' checked' if k in choice['graphics'] else ''}>"
                  f"{e(v)}</label>" for k, v in graphics.NAMES.items())
    return (f"<div class=\"edit\" data-beats=\"{e(json.dumps(choice['beats']))}\">"
            f"<div class=\"tl\" title=\"The Short's beats, as long as they play: pick one to preview and edit it\">{timeline}</div>"
            f"<label class=\"beatpick\">Preview beat{beat}</label>"
            f"<label>Mood{select('look', opts['look'], choice['look'])}</label>"
            f"<label>Captions{select('caption', opts['caption'], choice['caption'])}</label>"
            f"<label>Cuts{select('transition', opts['transition'], choice['transition'])}</label>"
            f"<label>This beat's mood{select('blook', {**same, **{k: v for k, v in opts['look'].items() if k}}, '')}</label>"
            f"<label>Cut into this beat{select('bcut', {**same, **opts['transition']}, '')}</label><span></span>"
            f"<div class=\"gfx\"><b>Motion graphics</b>{gfx}</div>"
            "<div class=\"tune\">"
            + slider("caption_size", "Caption size", choice["caption_size"], 0.05)
            + slider("caption_y", "Caption height", choice["caption_y"], 0.01)
            + slider("music_volume", "Music volume", music, 0.05)
            + f"<label class=\"check\"><input type=\"checkbox\" name=\"push\"{' checked' if choice['push'] else ''}>"
              "Slow push-in on still shots</label></div>"
            f"<div class=\"narr\" data-sample=\"{e(sample)}\" data-voice=\"{e(voice)}\" data-rate=\"{e(rate)}\">"
            f"<label>Voice<span class=\"vrow\">{select('voice', voices_for(lang), voice)}"
            "<button type=\"button\" class=\"listen\" title=\"Listen to this voice\">▶</button></span></label>"
            f"<label>Speed<span class=\"speeds\">{speeds}</span></label>"
            "<button class=\"setvoice\" hidden>Voice the Short again</button></div>"
            "<img alt=\"\"><button class=\"suggestedit\">✨ Suggest edit</button>"
            "<button class=\"saveedit\">Save edit</button><span class=\"hint\" id=\"editnote\"></span>"
            "<ul class=\"why\" id=\"editwhy\"></ul></div>")


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
        judge_html = "<p class=\"hint\">The hook judge needs Gemini (GEMINI_API_KEY in Settings).</p>"
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
                 f"<input class=\"clipfile\" type=\"file\" accept=\"video/*,image/*\" data-beat=\"{scene.n}\" hidden>"
                 f"{'Replace my clip' if mine else 'Upload your clip'}</label>"
                 + (f"<button class=\"remove\" data-beat=\"{scene.n}\">Remove my clip</button>" if mine else "")
                 + "</div>")
        my_voice = recording(Path(report["media"]), scene.n)
        voice_html = (f"<div class=\"mine voicebox\">"
                      + (f"<audio controls preload=\"none\" src=\"voice/{e(slot.voice)}?v={slot.length:.2f}\"></audio>"
                         if slot.voice else "")
                      + f"<button class=\"rec\" data-beat=\"{scene.n}\">● Record voice</button>"
                      f"<label class=\"upload\"><input class=\"voicefile\" type=\"file\" accept=\"audio/*\" "
                      f"data-beat=\"{scene.n}\" hidden>{'Replace my voice' if my_voice else 'Upload voice'}</label>"
                      + (f"<button class=\"voiceremove\" data-beat=\"{scene.n}\">Use the narrator</button>"
                         if my_voice else "") + "</div>")
        trim = ""
        if c.get("kind") == "video" and c["source"] not in PLACEHOLDERS and not ent.get("reuses_opening"):
            clip_len = duration(Path(c["file"]))
            if clip_len >= slot.length * 0.5 + 0.1:
                tools = tools.replace("</div>", "<button class=\"trimopen\">Trim</button></div>", 1)
                from . import trim_window

                t_start, t_end, _ = trim_window(clip_len, slot.length, float(c.get("start", 0.0)), c.get("end"))
                trim = (f"<div class=\"trim\" hidden data-beat=\"{scene.n}\" data-length=\"{slot.length:.3f}\" "
                        f"data-dur=\"{clip_len:.3f}\" data-pass=\"{match.PASS}\">"
                        f"<video muted playsinline controls preload=\"none\" "
                        f"data-src=\"/api/shorts/{e(quote(job.name))}/beats/{scene.n}/source\"></video>"
                        f"<div class=\"span\"><i></i></div>"
                        f"<div class=\"rl\"><span>Start</span></div>"
                        f"<input class=\"rs\" type=\"range\" min=\"0\" max=\"{clip_len:.2f}\" step=\"0.05\" value=\"{t_start:.2f}\">"
                        f"<div class=\"rl\"><span>End</span></div>"
                        f"<input class=\"re\" type=\"range\" min=\"0\" max=\"{clip_len:.2f}\" step=\"0.05\" value=\"{t_end:.2f}\">"
                        f"<div class=\"read\"></div>"
                        f"<div class=\"row\"><button class=\"trimcheck\">Check match</button>"
                        f"<button class=\"trimuse\">Use this stretch</button></div>"
                        f"<div class=\"result\"></div></div>")
        beats.append(
            f"<div class=\"beat{' flagged' if flagged else ''}\" id=\"beat-{scene.n}\"><img src=\"storyboard/{frame}\" alt=\"\">"
            f"<div class=\"head\"><span class=\"n\">{scene.n}</span><span class=\"time\">{slot.start:.1f}–"
            f"{slot.end:.1f}s</span></div><div class=\"ontext\">{e(scene.text)}</div>"
            f"<div class=\"vo\">{e(scene.voiceover)}</div><div class=\"visual\">{e(scene.visual)}</div>"
            f"<div class=\"src\">{e(src)}{badge_html}{opening}{link}</div>{_objects_html(ent)}"
            + (f"<div class=\"flags\">{flags}</div>" if flags else "") + tools + voice_html + trim + _how(ent) + "</div>")
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
<div class="panel"><h2>Edit</h2>{_edit_html(entries, edit.load(job), ep.script.lang, tl, job,
                                             next((s.voiceover for s in ep.script.scenes if s.voiceover), ep.title))}
<p class="hint">Mood grades every beat, captions restyle the spoken words, cuts add an effect between beats. Pick a
 beat on the timeline to preview it and give it its own mood or cut. Changing the narrator voices the whole Short again;
 a beat's <b>Record voice</b> or <b>Upload voice</b> puts your own voice on it.</p></div>
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
