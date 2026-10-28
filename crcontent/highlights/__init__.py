"""Smart Highlights: pick a finished video's most attractive 15–30 s for Shorts / Reels, with covers and a report.

audio structure (structure.py) + lyrics (lyrics_score.py) + visuals (visual.py) -> per-second scores -> candidate
clips snapped to bars and lyric lines (rank.py) -> optional Gemini judge (judge.py) -> covers (covers.py) ->
vertical renders through the usual finalize step (clip.py) -> report.json + report.html (report.py).
Weights and switches: <data folder>/highlights.json (settings.py).
"""
import json
from pathlib import Path


def make_highlights(target: Path, lyrics_file: Path | None = None, title: str = "", artist: str = "",
                    lang: str = "", render: bool = True, ai_judge: bool | None = None, log=print) -> Path:
    """Analyse `target` (a short-studio output folder or a video file), rank its highlights, make covers, render the
    best clips and write the report. Returns report.html."""
    from . import covers, lyrics_score, rank, report, settings, source, structure

    cfg = settings.load()
    log(f"[1/7] Reading {Path(target).name}")
    src = source.load(Path(target), lyrics_file, title, artist, lang, log=log)
    log(f"      {src.duration:.1f}s {src.size[0]}x{src.size[1]}, {len(src.lines)} lyric lines ({src.timing or 'none'}), "
        f"picture: {'lyric-free work/joined.mp4' if src.clean else src.video.name}")

    log("[2/7] Audio structure")
    st = structure.analyze(src.audio, cfg, src.song, src.lines, log=log)
    (src.out / "structure.json").write_text(json.dumps(st.to_json()), encoding="utf-8")
    log(f"      {st.method}: {st.bpm:.0f} bpm, {len(st.bars)} bars, sections: "
        + ", ".join(f"{s['name']} {s['start']:.0f}s" for s in st.sections))

    log("[3/7] Lyrics")
    lyr = lyrics_score.analyze(src.lines, src.title, src.duration, cfg)
    if not src.lines:  # clips start and end on lyric lines, so there's nothing to cut on
        raise RuntimeError("Smart Highlights needs the song's lyrics with timing: pass --lyrics FILE "
                           "(or run it on a music video folder that has lyrics.json).")
    best = max(range(len(src.lines)), key=lambda i: lyr.strength[i])
    log(f"      strongest line: \"{src.lines[best].text}\" (sung {lyr.parts[best]['count']}x)")
    scores = {"structure": structure.score(st, cfg), "lyrics": lyrics_score.score(lyr, cfg)}

    log("[4/7] Visuals")
    vis = None
    try:
        from . import visual

        vis = visual.analyze(src.clean or src.video, src.size, src.duration, cfg, log=log)
        scores["visual"] = visual.score(vis, cfg)
        (src.out / "visual.json").write_text(json.dumps({"cuts": vis.cuts, "per_second": vis.per_second}),
                                             encoding="utf-8")
        log(f"      {vis.method}: {len(vis.cuts)} scene cuts")
    except ImportError:
        log("      ! OpenCV isn't installed (pip install -r requirements-highlights.txt); ranking without visuals")

    log("[5/7] Ranking")
    cands = rank.candidates(src.lines, st, scores, lyr, cfg)
    if not cands:
        raise RuntimeError("No 15–30 s stretch fits between lyric lines; widen clip lengths in highlights.json.")
    count = int(cfg["clip"]["count"])
    use_judge = cfg["ai_judge"]["enabled"] if ai_judge is None else ai_judge
    pool = rank.pick(cands, max(count, int(cfg["ai_judge"]["candidates"]) if use_judge else count),
                     float(cfg["clip"]["repeat_penalty"]))
    for k, c in enumerate(pool, 1):
        log(f"      {k}. {c.start:6.1f}-{c.end:6.1f}s {c.section:<14} score {c.score:.3f}  \"{c.hook_line}\"")

    verdicts: dict[int, dict] = {}
    order = list(range(len(pool)))
    if use_judge:
        log(f"[6/7] AI judge (Gemini ranks {len(pool)} candidates)")
        from . import judge

        about = ", ".join(x for x in (getattr(src.song, "genre", ""), getattr(src.song, "mood", "")) if x)
        from .clip import full_song

        artist = full_song(src)[0]  # the artist, else the channel the music video is on (for its hashtag)
        ranked = judge.rank(pool, src.clean or src.video, src.size, src.title, artist, src.lang, cfg, about, log)
        if ranked:
            verdicts = {r["candidate"]: r for r in ranked}
            order = [r["candidate"] for r in ranked] + [k for k in order if k not in verdicts]
            log("      Gemini's order: " + ", ".join(str(k + 1) for k in order))
    else:
        log("[6/7] AI judge: off (highlights.json \"ai_judge\")")

    log("[7/7] Covers, clips and report")
    entries = []
    for pos, k in enumerate(order, 1):
        c = pool[k]
        folder = src.out / f"candidate_{k + 1}"
        folder.mkdir(exist_ok=True)
        v = verdicts.get(k, {})
        # the cover says what the clip is about (its hook) when Gemini wrote one; else the song's name
        made = covers.make_covers(src.clean or src.video, src.size, c.start, c.end, v.get("hook_text") or src.title,
                                  src.artist, folder, cfg)
        entries.append({"candidate": k + 1, "final_rank": pos, "score_rank": k + 1, **c.to_json(),
                        "ai": v or None, "hook_text": v.get("hook_text", c.hook_line),
                        "caption": v.get("caption", ""), "covers": [{**m, "file": f"{folder.name}/{m['file']}"}
                                                                    for m in made], "video": None})
    if render:
        for e in entries[:count]:
            c = pool[e["candidate"] - 1]
            cover = src.out / e["covers"][0]["file"] if e["covers"] else None
            log(f"      rendering #{e['final_rank']}: {c.start:.1f}-{c.end:.1f}s")
            from . import clip

            subject_y = e["covers"][0].get("subject_y") if e["covers"] else None
            job = clip.render(src, c, e["final_rank"], e["hook_text"] if e["ai"] else "", e["ai"], cover, cfg,
                              subject_y, log)
            e["video"] = str(job / "video.mp4")
            e["job"] = job.name
            log(f"      -> {job}")
    data = {"title": src.title, "artist": src.artist, "lang": src.lang, "video": str(src.video),
            "duration": src.duration, "timing": src.timing, "structure_method": st.method,
            "visual_method": vis.method if vis else "", "judge": bool(verdicts), "weights": cfg["weights"],
            "sections": st.sections, "candidates": entries, "chosen": [e["candidate"] for e in entries[:count]],
            "curve": {k: [round(x, 3) for x in v] for k, v in scores.items()}}
    (src.out / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    page = report.write(data, src.out)
    log(f"Done: {page}")
    return page
