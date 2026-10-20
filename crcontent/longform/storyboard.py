"""The storyboard: every scene with its footage, on-screen text and voiceover, to check before anything is rendered.

storyboard.html sits in the job folder. It opens from disk to look at; opened from the engine
(http://127.0.0.1:8000/media/<job>/storyboard.html, which make.py --storyboard starts) it can also swap a scene's
footage for one of its alternatives, search again with other words, pick up files you put in the media folder, and
approve: rendering only starts from an approved storyboard, and approving again is needed after any change.
"""
import hashlib
import json
from pathlib import Path

from .parse import Script, stamp
from .timing import Timeline

APPROVAL = "approved.json"

CSS = """
:root { --bg:#f6f5f2; --card:#ffffff; --ink:#1d1d1f; --soft:#6b6b70; --line:#e4e2dc; --accent:#d9480f; --warn:#c92a2a;
  --warnbg:#fff5f5; --ok:#2b8a3e; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#131316; --card:#1c1c20; --ink:#ececf0;
  --soft:#9a9aa3; --line:#2c2c33; --accent:#ff8a4c; --warn:#ff8787; --warnbg:#2a1717; --ok:#69db7c; } }
:root[data-theme="dark"] { --bg:#131316; --card:#1c1c20; --ink:#ececf0; --soft:#9a9aa3; --line:#2c2c33; --accent:#ff8a4c;
  --warn:#ff8787; --warnbg:#2a1717; --ok:#69db7c; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 "Segoe UI", system-ui, sans-serif; }
main { max-width:1180px; margin:0 auto; padding:28px 16px 120px; }
h1 { font-size:28px; margin:0 0 4px; letter-spacing:-0.01em; }
.meta { color:var(--soft); margin:0 0 18px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 18px; margin-bottom:16px; }
.panel h2 { font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--soft); margin:0 0 8px; }
.notes li { color:var(--warn); }
.chapters { display:flex; flex-wrap:wrap; gap:6px 16px; font-size:14px; font-variant-numeric:tabular-nums; }
.chapters s { color:var(--soft); }
.part { font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--soft); margin:26px 0 8px; }
.scene { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px; margin-bottom:12px;
  display:grid; grid-template-columns:340px 1fr; gap:18px; }
.scene.flagged { border-color:var(--warn); }
.pic { position:relative; }
.pic img { width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:10px; display:block; background:#000; }
.pic .kind { position:absolute; left:8px; top:8px; font-size:11px; padding:1px 7px; border-radius:99px; background:#000a;
  color:#fff; }
.src { font-size:12px; color:var(--soft); margin-top:6px; overflow-wrap:anywhere; }
.src a { color:inherit; }
.head { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
.n { font-size:22px; font-weight:800; color:var(--accent); line-height:1; }
.time { font-weight:650; font-variant-numeric:tabular-nums; }
.planned { color:var(--soft); font-size:13px; font-variant-numeric:tabular-nums; }
.tag { font-size:12px; padding:1px 8px; border-radius:99px; background:var(--bg); border:1px solid var(--line); color:var(--soft); }
.ontext { font-size:19px; font-weight:750; margin:6px 0 2px; }
.vo { margin:4px 0; }
.visual { color:var(--soft); font-size:14px; }
audio { width:100%; height:32px; margin-top:6px; }
.flags { margin:8px 0 0; padding:6px 10px; background:var(--warnbg); border-radius:8px; color:var(--warn); font-size:13px; }
.flags div + div { margin-top:3px; }
.alts { display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-top:10px; }
.alt { font-size:11px; color:var(--soft); } .alt a { color:inherit; }
.alt img { width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:6px; display:block; background:#000; }
.alt button { width:100%; margin-top:3px; }
.score.bad { color:var(--warn); } .score.good { color:var(--ok); }
.tools { display:flex; gap:6px; margin-top:10px; flex-wrap:wrap; }
.tools input { flex:1; min-width:180px; font:inherit; padding:5px 9px; border-radius:8px; border:1px solid var(--line);
  background:var(--bg); color:var(--ink); }
button { font:13px "Segoe UI", system-ui, sans-serif; padding:5px 11px; border-radius:8px; border:1px solid var(--line);
  background:var(--card); color:var(--ink); cursor:pointer; }
button:disabled { opacity:.5; cursor:default; }
button.primary { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:650; padding:9px 18px; font-size:15px; }
.hint { font-size:12px; color:var(--soft); margin-top:6px; }
.bar { position:fixed; left:0; right:0; bottom:0; background:var(--card); border-top:1px solid var(--line); padding:12px 16px; }
.bar > div { max-width:1180px; margin:0 auto; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
.bar .status { flex:1; min-width:200px; color:var(--soft); font-size:14px; }
progress { width:220px; }
@media (max-width: 760px) { .scene { grid-template-columns:1fr; } .alts { grid-template-columns:repeat(2, 1fr); } }
"""

SCRIPT = r"""
const S = JSON.parse(document.getElementById('state').textContent);
const live = location.protocol.startsWith('http') && location.pathname.startsWith('/media/');
const job = live ? decodeURIComponent(location.pathname.split('/')[2]) : '';
const api = (p) => `/api/longform/${encodeURIComponent(job)}${p}`;
const $ = (sel) => document.querySelector(sel);
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v); else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false)
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  return el;
}
const clock = (t) => { t = Math.round(t); const m = Math.floor(t / 60), s = t % 60; return `${m}:${String(s).padStart(2, '0')}`; };
const small = (url) => (url || '').replace(/\/(\d+)px-/, '/330px-');
const stamp = Date.now();
async function call(path, body) {
  const r = await fetch(api(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
}
function score(c) {
  if (c === undefined || c === null) return null;
  return h('span', { class: 'score ' + (c >= 7 ? 'good' : 'bad') }, ` · ${c}/10`);
}
function sceneEl(i) {
  const sc = S.scenes[i], slot = S.slots[i], f = S.footage[i], c = f.chosen;
  const busy = (el, on) => el.querySelectorAll('button, input').forEach(b => b.disabled = on || !live);
  const row = h('section', { class: 'scene' + (f.flags.length ? ' flagged' : ''), id: `scene-${sc.n}` });
  const thumb = `storyboard/scene-${String(sc.n).padStart(2, '0')}.jpg?v=${f.v || stamp}`;
  const made = { own: 'your file', placeholder: 'placeholder card', card: 'card drawn by the app',
    montage: `montage of ${(c.parts || []).length} other scenes` };
  const src = made[c.source] || [c.source, c.kind, c.author && `by ${c.author}`].filter(Boolean).join(' ');
  const left = h('div', { class: 'pic' },
    h('img', { src: thumb, alt: `Scene ${sc.n}: ${sc.visual}`, loading: 'lazy' }),
    h('span', { class: 'kind' }, c.source === 'montage' ? 'montage' : c.source === 'card' ? 'card'
      : c.kind === 'video' ? 'video' : c.source === 'placeholder' ? 'placeholder' : 'photo · slow zoom'),
    h('div', { class: 'src' }, src, score(c.check),
      c.licence ? [' · ', c.licence_url ? h('a', { href: c.licence_url, target: '_blank', rel: 'noreferrer' }, c.licence) : c.licence] : null,
      c.page ? [' · ', h('a', { href: c.page, target: '_blank', rel: 'noreferrer' }, 'source')] : null,
      c.kind === 'video' && c.duration ? ` · ${c.duration} s clip` : null));
  const role = sc.rank ? 'title card' : sc.text ? 'lower third' : null;
  const alts = h('div', { class: 'alts' }, f.alternatives.map((a, k) => h('div', { class: 'alt' },
    h('img', { src: small(a.thumb), alt: `${a.source} ${a.kind}`, loading: 'lazy' }),
    h('div', {}, `${a.source} ${a.kind}`, a.duration ? ` ${a.duration}s` : '', score(a.check),
      a.kind === 'video' && a.url ? [' · ', h('a', { href: a.url, target: '_blank', rel: 'noreferrer' }, 'preview')] : null),
    h('button', { disabled: !live, onclick: async (e) => {
      busy(row, true); e.target.textContent = 'Using…';
      try { replace(i, await call(`/scenes/${sc.n}/pick`, { key: altKey(a) })); } catch (err) { alert(err.message); busy(row, false); }
    } }, 'Use this'))));
  const q = h('input', { value: f.query, 'aria-label': `Search words for scene ${sc.n}`, disabled: !live });
  const tools = h('div', { class: 'tools' }, q,
    h('button', { disabled: !live, onclick: async (e) => {
      busy(row, true); e.target.textContent = 'Searching…';
      try { replace(i, await call(`/scenes/${sc.n}/search`, { query: q.value })); } catch (err) { alert(err.message); busy(row, false); }
    } }, 'Search again'));
  const right = h('div', {},
    h('div', { class: 'head' }, h('span', { class: 'n' }, `#${sc.n}`),
      h('span', { class: 'time' }, `${clock(slot.start)}–${clock(slot.end)}`),
      h('span', { class: 'planned' }, `planned ${clock(sc.planned)} · ${slot.length.toFixed(1)} s`),
      role && h('span', { class: 'tag' }, role),
      f.kind && f.kind !== 'footage' && h('span', { class: 'tag' }, f.kind),
      f.subject && h('span', { class: 'tag' }, f.subject.split(':')[0])),
    sc.text && h('div', { class: 'ontext' }, sc.text),
    h('div', { class: 'vo' }, sc.voiceover || h('i', {}, '(no voiceover)')),
    slot.voice && h('audio', { controls: true, preload: 'none', src: `voice/${slot.voice}` }),
    h('div', { class: 'visual' }, 'Visual: ', sc.visual),
    f.flags.length ? h('div', { class: 'flags' }, f.flags.map(t => h('div', {}, '⚠ ', t))) : null,
    f.alternatives.length ? alts : null, tools,
    h('div', { class: 'hint' }, `Or put your own clip or photo in ${S.media}\\scene-${String(sc.n).padStart(2, '0')}.mp4 (.jpg, .png…) and press "Reload my files".`));
  row.append(left, right);
  return row;
}
const altKey = (a) => `${a.source}-${a.kind}-${a.id}`;
function replace(i, entry) {
  entry.v = Date.now(); S.footage[i] = entry; S.approved = false;
  document.getElementById(`scene-${S.scenes[i].n}`).replaceWith(sceneEl(i));
  bar();
}
function render() {
  const list = $('#scenes'); list.textContent = ''; let part = null;
  S.scenes.forEach((sc, i) => {
    if (sc.part !== part) { part = sc.part; list.append(h('div', { class: 'part' }, part)); }
    list.append(sceneEl(i));
  });
  bar();
}
function bar(msg) {
  const flagged = S.footage.filter(f => f.flags.length).length;
  $('#status').textContent = msg || (!live
    ? 'Opened from disk: to swap footage and approve, run  python make.py --storyboard "<this folder>"  (or open it from the app).'
    : S.approved ? 'Approved. Rendering starts from this storyboard; any change needs approving again.'
    : `${S.footage.length} scenes, ${flagged} flagged. Check every scene, then approve to render.`);
  $('#approve').disabled = !live || S.rendering;
  $('#reload').disabled = !live || S.rendering;
}
$('#reload').addEventListener('click', async () => {
  bar('Looking for your files…');
  try { const r = await call('/reload'); S.footage = r.footage; S.approved = false; render(); bar(`${r.found} of your files in use.`); }
  catch (err) { bar(err.message); }
});
$('#approve').addEventListener('click', async () => {
  const flagged = S.footage.filter(f => f.flags.length).length;
  if (flagged && !confirm(`${flagged} scene(s) are still flagged. Render anyway?`)) return;
  S.rendering = true; bar('Starting the render…');
  try {
    const { id } = await call('/approve');
    S.approved = true; const p = $('#progress'); p.hidden = false;
    const tick = async () => {
      const j = await (await fetch(`/api/jobs/${id}`)).json();
      p.value = Math.max(j.step - 1, 0); p.max = 7;
      const last = (j.log || []).filter(l => !l.startsWith('[')).slice(-1)[0] || '';
      if (j.status === 'done') { S.rendering = false; p.hidden = true; $('#status').textContent = '';
        $('#status').append('Done: ', h('a', { href: 'video.mp4' }, 'video.mp4'), ' · ', h('a', { href: 'description.txt' }, 'description.txt'),
          ' · ', h('a', { href: 'captions.srt' }, 'captions.srt'), ' · ', h('a', { href: 'credits.txt' }, 'credits.txt')); return; }
      if (j.status === 'error') { S.rendering = false; p.hidden = true; bar('Render failed: ' + (j.error || '')); return; }
      $('#status').textContent = `Rendering · step ${j.step}/7 · ${last.trim()}`;
      setTimeout(tick, 1500);
    };
    tick();
  } catch (err) { S.rendering = false; bar(err.message); }
});
render();
"""


def fingerprint(job: Path) -> str:
    """What an approval is for: the footage picked and the timeline (any swap or re-voice changes it)."""
    entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
    picks = [(e["scene"], e["chosen"]["file"]) for e in entries]
    timeline = json.loads((job / "timeline.json").read_text(encoding="utf-8"))
    data = json.dumps([picks, [(s["scene"], s["length"], s["voice"]) for s in timeline["slots"]]])
    return hashlib.sha1(data.encode()).hexdigest()


def approved(job: Path) -> bool:
    path = job / APPROVAL
    try:
        return json.loads(path.read_text(encoding="utf-8"))["fingerprint"] == fingerprint(job)
    except (OSError, ValueError, KeyError):
        return False


def approve(job: Path) -> None:
    from datetime import datetime

    (job / APPROVAL).write_text(json.dumps({"fingerprint": fingerprint(job),
                                            "at": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")


def write(job: Path, media: Path) -> Path:
    """storyboard.html from the job's scenes.json, timeline.json and footage.json."""
    import html

    script = Script.load(job / "scenes.json")
    tl = Timeline.from_json(json.loads((job / "timeline.json").read_text(encoding="utf-8")))
    entries = json.loads((job / "footage.json").read_text(encoding="utf-8"))
    state = {"scenes": [s.__dict__ for s in script.scenes], "slots": [{**s.__dict__, "end": s.end} for s in tl.slots],
             "footage": entries, "media": str(media), "approved": approved(job)}
    flagged = sum(1 for e in entries if e["flags"])
    from ..packaging import fluff_opening

    fluff = fluff_opening(" ".join(s.voiceover for s in script.scenes[:2]))
    notes = ([f"the opening has {' and '.join(fluff)}: start with the payoff instead, no intro"] * bool(fluff)
             + tl.notes + [f"{flagged} scene(s) flagged: check them below"] * bool(flagged))
    chapters = " ".join(f"<span><b>{stamp(c['at'])}</b> {html.escape(c['title'])} <s>{stamp(c['planned'])}</s></span>"
                        for c in tl.chapters)
    data = json.dumps(state, ensure_ascii=False).replace("</", "<\/")  # safe inside <script>
    checks = ""
    if notes:
        checks = ('<div class="panel"><h2>Check</h2><ul class="notes">'
                  + "".join(f"<li>{html.escape(n)}</li>" for n in notes) + "</ul></div>")
    body = f"""<!doctype html>
<html lang="{script.lang}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Storyboard · {html.escape(script.title)}</title><style>{CSS}</style></head>
<body><main>
<h1>{html.escape(script.title)}</h1>
<p class="meta">Storyboard · {len(script.scenes)} scenes · {stamp(tl.total)} from the real voiceover
 (the script planned {stamp(tl.planned_total)})</p>
{checks}
<div class="panel"><h2>Chapters (real time, <s>planned</s>)</h2><div class="chapters">{chapters}</div></div>
<div id="scenes"></div>
</main>
<div class="bar"><div><span class="status" id="status"></span><progress id="progress" hidden></progress>
<button id="reload">Reload my files</button><button class="primary" id="approve">Approve and render</button></div></div>
<script type="application/json" id="state">{data}</script>
<script>{SCRIPT}</script>
</body></html>"""
    out = job / "storyboard.html"
    out.write_text(body, encoding="utf-8")
    return out
