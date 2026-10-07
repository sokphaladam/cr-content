const $ = (sel) => document.querySelector(sel);

const state = {
  options: null,
  lang: "en",
  topic: "",
  selected: null,   // library folder name currently shown in the preview
  pollTimer: null,
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function setMsg(el, text, isError = false) {
  el.textContent = text;
  el.classList.toggle("error", isError);
}

function setBusy(btn, busy, label) {
  btn.disabled = busy;
  btn.classList.toggle("busy", busy);
  if (label) btn.textContent = label;
}

/* ---------- Options & key status ---------- */

async function loadOptions() {
  state.options = await api("/api/options");
  const { keys, music } = state.options;
  $("#keys").innerHTML = [
    keys.anthropic
      ? `<span class="key">Claude connected</span>`
      : `<span class="key missing" title="Add ANTHROPIC_API_KEY (sk-ant-...) to .env and restart">Claude key missing</span>`,
    keys.stock
      ? `<span class="key">Stock footage: ${keys.stock === "pixabay" ? "Pixabay" : "Pexels"}</span>`
      : `<span class="key soft" title="Add a free PIXABAY_API_KEY to .env for real footage">Gradient backgrounds</span>`,
  ].join("");
  $("#music").innerHTML =
    (music.length ? `<option value="">Random track</option>` : "") +
    `<option value="none">No music</option>` +
    music.map((m) => `<option value="${esc(m)}">${esc(m.replace(/\.mp3$/i, ""))}</option>`).join("");
  if (!keys.anthropic) {
    setMsg($("#createMsg"), "Claude isn't connected, so scripts can't be written for you yet. Use “Write it myself”, or add your key to .env and restart.");
  }
}

function fillVoices(lang, selected) {
  const voices = state.options?.langs[lang]?.voices || [];
  $("#voice").innerHTML = voices
    .map((v) => {
      const label = v.replace(/Neural$/, "").split("-").slice(2).join(" ") + ` (${v.split("-").slice(0, 2).join("-")})`;
      return `<option value="${esc(v)}"${v === selected ? " selected" : ""}>${esc(label)}</option>`;
    })
    .join("");
}

/* ---------- Views ---------- */

function showCreate() {
  $("#createView").hidden = false;
  $("#editView").hidden = true;
  $("#topic").focus();
}

function showEdit(script, lang, topic) {
  state.lang = lang;
  state.topic = topic || "";
  $("#editLang").textContent = state.options.langs[lang].name;
  $("#translateBtn").textContent = `Translate to ${otherLangLabel(lang)}`;
  $("#title").value = script.title || "";
  $("#title").lang = lang;
  $("#caption").value = script.caption || "";
  $("#caption").lang = lang;
  $("#hashtags").value = (script.hashtags || []).map((h) => "#" + h).join(" ");
  $("#scenes").innerHTML = "";
  (script.scenes.length ? script.scenes : [{}]).forEach((s) => addScene(s));
  fillVoices(lang);
  setMsg($("#editMsg"), "");
  setMsg($("#translateMsg"), "");
  stopPreview();
  $("#createView").hidden = true;
  $("#editView").hidden = false;
  window.scrollTo({ top: 0 });
}

function renumber() {
  [...$("#scenes").children].forEach((li, i) => (li.querySelector(".scene-num").textContent = i + 1));
}

function addScene(scene = {}, after = null) {
  const li = $("#sceneTpl").content.firstElementChild.cloneNode(true);
  li.querySelector(".narration").value = scene.narration || "";
  li.querySelector(".narration").lang = state.lang;
  li.querySelector(".visual").value = scene.visual_query || "";
  li.querySelector(".headline").value = scene.on_screen_text || "";
  li.querySelector(".headline").lang = state.lang;
  setupMedia(li, scene.media || "");
  li.querySelector(".scene-listen").onclick = (e) => listen(e.currentTarget, li.querySelector(".narration").value);
  li.querySelector(".up").onclick = () => { li.previousElementSibling?.before(li); renumber(); };
  li.querySelector(".down").onclick = () => { li.nextElementSibling?.after(li); renumber(); };
  li.querySelector(".remove").onclick = () => {
    if ($("#scenes").children.length > 1) { li.remove(); renumber(); }
  };
  after ? after.after(li) : $("#scenes").append(li);
  renumber();
  return li;
}

function collectScript() {
  const scenes = [...$("#scenes").children]
    .map((li) => ({
      narration: li.querySelector(".narration").value.trim(),
      visual_query: li.querySelector(".visual").value.trim() || "abstract background",
      on_screen_text: li.querySelector(".headline").value.trim(),
      media: li.dataset.media || "",
    }))
    .filter((s) => s.narration);
  return {
    title: $("#title").value.trim() || "Untitled video",
    scenes,
    caption: $("#caption").value.trim(),
    hashtags: $("#hashtags").value.split(/[\s,]+/).map((h) => h.replace(/^#/, "")).filter(Boolean),
  };
}

/* ---------- Voice preview ---------- */

const SAMPLE_TEXT = {
  en: "Did you know octopuses have three hearts? Follow for more.",
  km: "តើអ្នកដឹងទេ ថាមឹកដៃប្រាំបី មានបេះដូងបី? តាមដានយើង ដើម្បីដឹងបន្ថែម។",
};
const preview = { audio: new Audio(), btn: null, url: null };

function stopPreview() {
  preview.audio.pause();
  if (preview.btn) preview.btn.classList.remove("playing", "busy");
  preview.btn = null;
}
preview.audio.onended = stopPreview;

async function listen(btn, text) {
  if (preview.btn === btn) { stopPreview(); return; }   // second click = stop
  stopPreview();
  text = (text || "").trim();
  const voice = $("#voice").value;
  if (!text) { setMsg($("#editMsg"), "Write some narration first, then listen.", true); return; }
  preview.btn = btn;
  btn.classList.add("busy");
  try {
    const res = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice, rate: $("#rate").value }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Preview failed (${res.status})`);
    const blob = await res.blob();
    if (preview.btn !== btn) return;                       // user clicked something else meanwhile
    if (preview.url) URL.revokeObjectURL(preview.url);
    preview.url = URL.createObjectURL(blob);
    preview.audio.src = preview.url;
    btn.classList.remove("busy");
    btn.classList.add("playing");
    await preview.audio.play();
  } catch (err) {
    stopPreview();
    setMsg($("#editMsg"), err.message, true);
  }
}

$("#listenVoice").onclick = () => {
  const first = document.querySelector("#scenes .narration")?.value.trim();
  listen($("#listenVoice"), first || SAMPLE_TEXT[state.lang]);
};
$("#voice").onchange = stopPreview;
$("#rate").onchange = stopPreview;

/* ---------- Translate ---------- */

const otherLang = (lang) => (lang === "km" ? "en" : "km");
const otherLangLabel = (lang) => (otherLang(lang) === "km" ? "ខ្មែរ" : "English");

$("#translateBtn").onclick = async () => {
  const script = collectScript();
  if (!script.scenes.length) {
    setMsg($("#translateMsg"), "Write the narration for at least one scene first.", true);
    return;
  }
  const target = otherLang(state.lang);
  const btn = $("#translateBtn");
  setBusy(btn, true, "Translating…");
  setMsg($("#translateMsg"), "Claude is translating the narration, headlines and caption. Backgrounds stay the same.");
  try {
    const translated = await api("/api/translate", { method: "POST", body: { script, target } });
    showEdit(translated, target, state.topic);
    setMsg($("#translateMsg"),
      `Translated to ${state.options.langs[target].name}. Check the text, then render. Your original video stays in the library.`);
  } catch (err) {
    setMsg($("#translateMsg"), err.message, true);
  } finally {
    setBusy(btn, false, `Translate to ${otherLangLabel(state.lang)}`);
  }
};

/* ---------- Scene backgrounds ---------- */

let sceneUid = 0;
const IMAGE_RE = /\.(jpe?g|png|webp)$/i;

function setMedia(li, media) {
  li.dataset.media = media || "";
  const slot = li.querySelector(".media-slot");
  slot.classList.toggle("has-media", !!media);
  li.querySelector(".clear-media").hidden = !media;
  if (!media) {
    slot.innerHTML = `<span class="media-auto">Auto</span>`;
    slot.title = "Footage is picked automatically from the search words";
    return;
  }
  const url = "/" + media.split("/").map(encodeURIComponent).join("/");
  slot.title = "Your chosen background";
  slot.innerHTML = IMAGE_RE.test(media)
    ? `<img src="${url}" alt=""><span class="kind">Photo</span>`
    : `<video src="${url}#t=0.5" muted playsinline preload="metadata"></video><span class="kind">Video</span>`;
  const v = slot.querySelector("video");
  if (v) {
    slot.onmouseenter = () => v.play().catch(() => {});
    slot.onmouseleave = () => v.pause();
  }
}

function mediaMsg(li, text, isError = false) {
  const el = li.querySelector(".media-msg");
  el.textContent = text;
  el.classList.toggle("error", isError);
}

function setupMedia(li, media) {
  const uid = ++sceneUid;
  li.querySelectorAll('.picker .seg input').forEach((r) => (r.name = `kind-${uid}`));
  setMedia(li, media);

  const picker = li.querySelector(".picker");
  const q = li.querySelector(".picker-q");
  const kind = () => li.querySelector(`input[name="kind-${uid}"]:checked`).value;

  const openPicker = () => {
    const opening = picker.hidden;
    picker.hidden = !opening;
    li.querySelector(".find-btn").textContent = opening ? "Close search" : "Find footage";
    if (opening) {
      q.value = q.value || li.querySelector(".visual").value || "";
      q.focus();
      if (q.value && !li.querySelector(".results").children.length) runSearch();
    }
  };
  li.querySelector(".find-btn").onclick = openPicker;
  li.querySelector(".media-slot").onclick = openPicker;
  li.querySelector(".clear-media").onclick = () => { setMedia(li, ""); mediaMsg(li, ""); };

  const runSearch = async () => {
    const results = li.querySelector(".results");
    if (!q.value.trim()) return;
    results.innerHTML = "";
    mediaMsg(li, "Searching…");
    try {
      const data = await api(`/api/footage?q=${encodeURIComponent(q.value.trim())}&kind=${kind()}`);
      mediaMsg(li, data.results.length ? "" : "Nothing found. Try simpler words, or ask Claude for ideas.");
      results.innerHTML = data.results.map((r) => `
        <li><button type="button" class="result" data-id="${r.id}" data-kind="${r.kind}" data-source="${r.source}"
          style="background-image:url('${esc(r.thumb)}')" aria-label="Use this ${r.kind}${r.author ? " by " + esc(r.author) : ""}">
          ${r.kind === "video" ? `<span class="dur">${r.duration}s</span>` : ""}
        </button></li>`).join("");
      results.querySelectorAll(".result").forEach((b) => (b.onclick = () => pick(b)));
    } catch (err) {
      mediaMsg(li, err.message, true);
    }
  };
  li.querySelector(".picker-go").onclick = runSearch;
  q.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); runSearch(); } };
  li.querySelectorAll(`input[name="kind-${uid}"]`).forEach((r) => (r.onchange = runSearch));

  const pick = async (btn) => {
    btn.classList.add("loading");
    mediaMsg(li, "Downloading…");
    try {
      const m = await api("/api/footage/pick", { method: "POST", body: { source: btn.dataset.source, kind: btn.dataset.kind, id: +btn.dataset.id } });
      setMedia(li, m.media);
      li.querySelector(".visual").value = q.value.trim();
      mediaMsg(li, `${m.kind === "photo" ? "Photo" : "Video"} set for this scene.`);
      openPicker();
    } catch (err) {
      mediaMsg(li, err.message, true);
    } finally {
      btn.classList.remove("loading");
    }
  };

  li.querySelector(".ideas-btn").onclick = async (e) => {
    const btn = e.currentTarget;
    const ideas = li.querySelector(".ideas");
    setBusy(btn, true);
    try {
      const data = await api("/api/ideas", {
        method: "POST",
        body: { narration: li.querySelector(".narration").value, current: q.value || li.querySelector(".visual").value },
      });
      ideas.innerHTML = data.queries.map((x) => `<button type="button" class="idea">${esc(x)}</button>`).join("");
      ideas.querySelectorAll(".idea").forEach((b) => (b.onclick = () => { q.value = b.textContent; runSearch(); }));
    } catch (err) {
      mediaMsg(li, err.message, true);
    } finally {
      setBusy(btn, false);
    }
  };

  li.querySelector(".upload-input").onchange = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    mediaMsg(li, `Uploading ${file.name}…`);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Upload failed (${res.status})`);
      setMedia(li, data.media);
      mediaMsg(li, `${data.kind === "photo" ? "Photo" : "Video"} uploaded.`);
    } catch (err) {
      mediaMsg(li, err.message, true);
    }
  };
}

/* ---------- Create: write script ---------- */

$("#seconds").oninput = (e) => ($("#secondsOut").textContent = `${e.target.value} s`);
$("#sceneCount").oninput = (e) => ($("#sceneOut").textContent = e.target.value);
document.querySelectorAll('input[name="lang"]').forEach((r) =>
  r.addEventListener("change", () => {
    const km = r.value === "km" && r.checked;
    $("#topic").lang = km ? "km" : "en";
    $("#topic").placeholder = km ? "ប្រវត្តិប្រាសាទអង្គរវត្ត" : "3 weird facts about octopuses";
  })
);

$("#createForm").onsubmit = async (e) => {
  e.preventDefault();
  const lang = document.querySelector('input[name="lang"]:checked').value;
  const topic = $("#topic").value.trim();
  const btn = $("#writeBtn");
  setBusy(btn, true, "Claude is writing…");
  setMsg($("#createMsg"), "This usually takes 15–40 seconds.");
  try {
    const script = await api("/api/script", {
      method: "POST",
      body: { topic, lang, seconds: +$("#seconds").value, scenes: +$("#sceneCount").value, style: $("#style").value },
    });
    showEdit(script, lang, topic);
  } catch (err) {
    setMsg($("#createMsg"), err.message, true);
  } finally {
    setBusy(btn, false, "Write script with Claude");
  }
};

$("#blankBtn").onclick = () => {
  const lang = document.querySelector('input[name="lang"]:checked').value;
  const topic = $("#topic").value.trim();
  const n = +$("#sceneCount").value;
  showEdit({ title: topic, scenes: Array.from({ length: n }, () => ({})), caption: "", hashtags: [] }, lang, topic);
  $("#scenes .narration").focus();
};

$("#backBtn").onclick = showCreate;
$("#newBtn").onclick = () => { selectVideo(null); showCreate(); };
$("#addScene").onclick = () => addScene().querySelector(".narration").focus();

/* ---------- Render ---------- */

$("#renderBtn").onclick = async () => {
  const script = collectScript();
  if (!script.scenes.length) {
    setMsg($("#editMsg"), "Write the narration for at least one scene first.", true);
    return;
  }
  const btn = $("#renderBtn");
  setBusy(btn, true, "Rendering…");
  setMsg($("#editMsg"), "");
  try {
    const { id } = await api("/api/render", {
      method: "POST",
      body: { script, topic: state.topic, lang: state.lang, voice: $("#voice").value, rate: $("#rate").value, music: $("#music").value },
    });
    showProgress(script.title);
    pollJob(id);
  } catch (err) {
    setMsg($("#editMsg"), err.message, true);
    setBusy(btn, false, "Render video");
  }
};

function showProgress(title) {
  state.selected = null;
  markLibrary();
  $("#player").pause();
  $("#player").hidden = true;
  $("#screenIdle").hidden = true;
  $("#postCard").hidden = true;
  $("#screenProgress").hidden = false;
  $("#progressTitle").textContent = title;
  $("#log").textContent = "Waiting to start…";
  updateSteps(0, false);
}

function updateSteps(step, finished) {
  [...$("#steps").children].forEach((li, i) => {
    li.classList.toggle("done", finished || i + 1 < step);
    li.classList.toggle("active", !finished && i + 1 === step);
  });
}

function pollJob(id) {
  clearTimeout(state.pollTimer);
  const tick = async () => {
    let job;
    try {
      job = await api(`/api/jobs/${id}`);
    } catch (err) {
      $("#log").innerHTML = `<span class="err">${esc(err.message)}</span>`;
      setBusy($("#renderBtn"), false, "Render video");
      return;
    }
    $("#log").textContent = job.log.join("\n") || (job.status === "queued" ? "Waiting for the previous render to finish…" : "");
    $("#log").scrollTop = $("#log").scrollHeight;
    updateSteps(job.step, job.status === "done");
    if (job.status === "done") {
      setBusy($("#renderBtn"), false, "Render video");
      setMsg($("#editMsg"), "Video ready. Edit the script and render again to make another version.");
      await loadLibrary();
      selectVideo(job.video);
    } else if (job.status === "error") {
      setBusy($("#renderBtn"), false, "Render video");
      $("#log").innerHTML += `\n<span class="err">${esc(job.error)}</span>`;
      setMsg($("#editMsg"), "Rendering failed. The details are in the preview panel.", true);
    } else {
      state.pollTimer = setTimeout(tick, 1000);
    }
  };
  tick();
}

/* ---------- Library ---------- */

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + ", " +
    d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

async function loadLibrary() {
  const items = await api("/api/videos");
  const list = $("#libraryList");
  if (!items.length) {
    list.innerHTML = `<li class="library-empty">Videos you render appear here.</li>`;
    return;
  }
  list.innerHTML = items
    .map((v) => `
      <li><button type="button" class="lib-item" data-name="${esc(v.name)}">
        <span class="lib-thumb" style="${v.thumb ? `background-image:url('/media/${encodeURIComponent(v.name)}/thumbnail.jpg')` : ""}"></span>
        <span><span class="lib-title" lang="${esc(v.lang)}">${esc(v.title)}</span>
        <span class="lib-meta">${v.lang === "km" ? "Khmer" : "English"}, ${esc(fmtDate(v.created))}${v.video ? "" : " (script only)"}</span></span>
      </button></li>`)
    .join("");
  list.querySelectorAll(".lib-item").forEach((b) => (b.onclick = () => selectVideo(b.dataset.name, true)));
  markLibrary();
}

function markLibrary() {
  document.querySelectorAll(".lib-item").forEach((b) => b.setAttribute("aria-current", String(b.dataset.name === state.selected)));
}

async function selectVideo(name, openScript = false) {
  state.selected = name;
  markLibrary();
  const player = $("#player");
  $("#screenProgress").hidden = true;
  if (!name) {
    player.pause();
    player.hidden = true;
    $("#postCard").hidden = true;
    $("#screenIdle").hidden = false;
    return;
  }
  const v = await api(`/api/videos/${encodeURIComponent(name)}`);
  const base = `/media/${encodeURIComponent(name)}`;
  if (v.video) {
    player.src = `${base}/video.mp4?t=${Date.now()}`;
    player.hidden = false;
    $("#screenIdle").hidden = true;
  } else {
    player.hidden = true;
    $("#screenIdle").hidden = false;
  }
  $("#postText").textContent = v.post || "No caption saved for this video.";
  $("#postText").lang = v.lang;
  $("#downloadBtn").href = `${base}/video.mp4`;
  $("#downloadBtn").hidden = !v.video;
  $("#postCard").hidden = false;
  if (openScript && v.script) showEdit(v.script, v.lang, "");
}

$("#copyBtn").onclick = async () => {
  await navigator.clipboard.writeText($("#postText").textContent);
  $("#copyBtn").textContent = "Copied";
  setTimeout(() => ($("#copyBtn").textContent = "Copy caption"), 1500);
};

$("#deleteBtn").onclick = async () => {
  const name = state.selected;
  if (!name) return;
  const btn = $("#deleteBtn");
  if (btn.dataset.confirm !== name) {
    btn.dataset.confirm = name;
    btn.textContent = "Click again to delete";
    setTimeout(() => { btn.dataset.confirm = ""; btn.textContent = "Delete"; }, 3000);
    return;
  }
  btn.dataset.confirm = "";
  btn.textContent = "Delete";
  await api(`/api/videos/${encodeURIComponent(name)}`, { method: "DELETE" });
  selectVideo(null);
  loadLibrary();
};

/* ---------- Boot ---------- */

(async () => {
  try {
    await loadOptions();
  } catch (err) {
    setMsg($("#createMsg"), `Couldn't load settings: ${err.message}`, true);
  }
  loadLibrary();
})();
