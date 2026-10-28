"""Footage for every beat of a Short, picked for the planned shot, not only the animal.

Per beat, in order:
1. your own file (<media_dir>/<plan>-epNN/scene-XX.*), used as it is
2. a beat that cuts back to the opening shot reuses the hook's clip
3. the beat's short searches (queries.py: "cat bath", "wet cat", "cat faucet"), each in Pixabay then Pexels (when its
   key is set): the best few clips of each are checked by Gemini for the planned shot (match.py) until one scores
   match.PASS or more; the hook beat's clips must also pass the motion rules (hook.py)
4. nothing matched: Gemini picks a simpler shot that stock likely has, and its searches are tried the same way
5. still nothing: a clip another Short used in the last 14 days, if that one matches (flagged)
6. still nothing: the best clip found if it at least shows the animal (match.GENERIC_MAX), flagged "needs your own
   clip"; else a placeholder card
No clip another Short uses can be a hook, and clips other Shorts used in the last 14 days are kept for step 5
(registry.py). Every query tried and every clip checked is kept in the entry's "search", for the pre-flight report.
"""
import json
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .. import visuals
from ..config import LLM_MODEL, OUTPUT_DIR
from ..importer import _keywords
from ..longform import footage as lf
from ..render import duration
from ..visuals import IMAGE_EXTS
from . import hook, match, queries
from .registry import Registry

PLACEHOLDERS = ("card", "placeholder")
PER_QUERY = 3            # clips checked from each search, so one loose search can't use up the beat's checks
CHECKS = 12              # clips checked by Gemini at most per beat on the planned shot
SIMPLER_CHECKS = 8       # ... and on the simpler shot
RECENT_TRIES = 3         # clips other Shorts used lately, checked at most when nothing else matched

ANIMAL_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "search": {"type": "string"},
                   "tags": {"type": "array", "items": {"type": "string"}}},
    "required": ["name", "search", "tags"],
    "additionalProperties": False,
}


def name_animal(ep, log=print) -> None:
    """ep.animal ("domestic house cat: small pet cat, not a big cat") and ep.animal_search ("cat"), from Gemini, or
    the word the title and Visual column use most."""
    if ep.animal:
        return
    shots = "\n".join(s.visual for s in ep.script.scenes)
    try:
        from ..script import make_client

        response = make_client().beta.messages.create(
            model=LLM_MODEL,
            max_tokens=300,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": ANIMAL_SCHEMA}},
            messages=[{"role": "user", "content": (
                f"A short animal-facts video: \"{ep.title}\"\nIts shots:\n{shots}\n\nWhich animal is it about? "
                "name: \"<common name>: <what tells it apart from look-alikes>\" (e.g. \"domestic house cat: small "
                "pet cat, not a big cat\"). search: the 1-2 words stock video sites tag it with (\"cat\"). tags: "
                "every single word a stock site might tag it with, singular and plural (\"cat\", \"cats\", "
                "\"kitten\", \"kittens\", \"kitty\").")}],
        )
        data = json.loads(next(b.text for b in response.content if b.type == "text"))
        ep.animal, ep.animal_search = data["name"].strip(), data["search"].strip().lower()
        ep.animal_tags = sorted({t.strip().lower() for t in data["tags"] if t.strip()})
    except Exception as e:
        words = Counter(w for line in [ep.title, *shots.splitlines()] for w in _keywords(line).split())
        ep.animal = ep.animal_search = (words.most_common(1)[0][0] if words else "animal")
        log(f"      ! couldn't name the animal with Gemini ({type(e).__name__}); using \"{ep.animal}\"")


def sources(cfg: dict) -> tuple[list[str], list[str]]:
    """(sources searched, sources skipped with why) in shorts.json's order."""
    use, skipped = [], []
    for s in cfg["footage"]["sources"]:
        if s == "pexels" and not visuals.pexels_key():
            skipped.append("pexels (no PEXELS_API_KEY: add it in Settings)")
        elif s == "pixabay" and not visuals.pixabay_key():
            skipped.append("pixabay (no PIXABAY_API_KEY: add it in Settings)")
        else:
            use.append(s)
    return use, skipped


def tagged(item: dict, words: set[str]) -> bool:
    """Whether a stock result is tagged with the animal (results without tags, Wikimedia's, pass)."""
    tags = item.get("tags")
    if tags is None:
        return True
    return bool(words & set(re.findall(r"[a-z]+", tags.lower())))


def fetch_preview(item: dict) -> Path:
    """A clip's small copy, to judge it by before the full file is downloaded (the full file when it has none)."""
    if item.get("kind") != "video" or not item.get("preview"):
        return lf.fetch(item)
    return visuals._download(item["preview"], visuals.STOCK_CACHE / f"{item['source']}-video-{item['id']}-preview.mp4")


def clip_start(path: Path, length: float) -> float:
    """Where a non-hook clip starts: past a stock clip's fade-in when there's room (render._start does the same)."""
    return 0.0 if path.suffix.lower() in IMAGE_EXTS else min(0.5, max(duration(path) - length, 0.0))


class Picker:
    def __init__(self, ep, tl, media: Path, out: Path, cfg: dict, registry: Registry, log=print):
        self.ep, self.tl, self.media, self.out, self.cfg, self.reg, self.log = ep, tl, media, out, cfg, registry, log
        self.sources, self.skipped_sources = sources(cfg)
        self.width = lf._size(cfg)[0]
        self.lock = threading.Lock()
        self.filtered = 0              # stock results skipped for not being tagged with the animal
        self.taken: set[str] = set()   # clips claimed by a beat of this Short
        a = ep.animal_search or "animal"
        self.animal_words = set(ep.animal_tags) | {a, f"{a}s", *a.split()}  # what its stock tags must include

    def claim(self, item: dict) -> bool:
        with self.lock:
            if lf.key(item) in self.taken:
                return False
            self.taken.add(lf.key(item))
            return True

    def release(self, item: dict) -> None:
        with self.lock:
            self.taken.discard(lf.key(item))

    def checks(self, is_hook: bool) -> bool:
        """Does Gemini look at this beat's clips? shorts.json footage.check: all (default) / hook / off."""
        mode = self.cfg.get("footage", {}).get("check", "all")
        return mode == "all" or (mode == "hook" and is_hook)

    def try_clip(self, item: dict, plan: dict, length: float, is_hook: bool, query: str, source: str) -> dict:
        """Download and judge one clip: an attempt {query, source, key, page, score, seen, missing, reject, ...}."""
        attempt = {"query": query, "source": source, "key": lf.key(item), "page": item.get("page", ""),
                   "score": None, "seen": "", "missing": [], "reject": ""}
        try:
            path = fetch_preview(item)
        except (requests.RequestException, OSError, ValueError, RuntimeError) as e:
            attempt["reject"] = f"couldn't download ({type(e).__name__})"
            return attempt
        scan = None
        if is_hook:
            scan = hook.scan(path, length)
            if scan.reject:
                attempt.update(reject=scan.reject, motion=round(scan.own, 2))
                return attempt
            start = scan.start
        else:
            start = clip_start(path, length)
        if self.checks(is_hook):
            try:
                m = match.check(path, self.ep.animal, plan["shot"], plan["key_objects"], start, length)
            except Exception as e:  # no Gemini: unchecked, and it can't count as a match
                attempt["reject"] = f"not checked ({type(e).__name__})"
                return attempt
        else:  # this beat is not sent to Gemini: its first tagged clip is used
            m = match.unchecked()
        if scan:
            hook.judged(scan, m)
            attempt["motion"] = round(scan.own, 2)
        attempt.update(score=m["score"], seen=m.get("seen", ""), missing=m.get("missing", []),
                       problem=m.get("problem", ""), reject=scan.reject if scan else "")
        attempt["_pick"] = {**item, "file": str(path), "check": m["score"], "problem": m.get("problem", ""),
                            "start": start, "focus": [m["x"], m["y"]], **match.evidence(m),
                            **({"hook": scan.to_json()} if scan else {})}
        return attempt

    def candidates(self, query: str, length: float, is_hook: bool, deferred: list, skipped: list) -> list:
        """(item, source) for `query`: the best PER_QUERY unclaimed clips of each source, in source order. Clips
        another Short uses are skipped for a hook; ones used lately go to `deferred` for the last resort."""
        out = []
        for source in self.sources:
            n = 0
            for m in lf.search(query, [source], self.width, length, self.log, portrait=True):
                if n >= PER_QUERY:
                    break
                if is_hook and m["kind"] != "video":
                    continue
                if not tagged(m, self.animal_words):  # Pixabay lists rain and chickens for "wet cat"
                    self.filtered += 1
                    continue
                with self.lock:
                    if lf.key(m) in self.taken:
                        continue
                if is_hook and (why := self.reg.hook_block(m)):
                    skipped.append({"query": query, "source": source, "key": lf.key(m), "page": m.get("page", ""),
                                    "reason": why})
                    continue
                if not is_hook and (recent := self.reg.recent(m)):
                    deferred.append((m, source, query, recent))
                    continue
                out.append((m, source))
                n += 1
        return out

    def search(self, plan: dict, length: float, is_hook: bool, budget: int, log_into: dict) -> dict | None:
        """The beat's searches in order until a clip matches; returns the best attempt (or None). Fills log_into's
        attempts, skipped and deferred."""
        best = None
        checks = 0
        for q in plan["queries"]:
            for item, source in self.candidates(q, length, is_hook, log_into["deferred"], log_into["skipped"]):
                if checks >= budget:
                    return best
                if not self.claim(item):
                    continue
                a = self.try_clip(item, plan, length, is_hook, q, source)
                checks += a["score"] is not None
                log_into["attempts"].append(a)
                if a["score"] is not None and not a["reject"] and (best is None or a["score"] > best["score"]):
                    if best:
                        self.release(best["_pick"])
                    best = a
                else:
                    self.release(item)
                if best and best["score"] >= match.PASS:
                    return best
        return best

    def own(self, entry: dict, scene, length: float, is_hook: bool) -> bool:
        path = lf.own_media(self.media, scene.n)
        if not path:
            return False
        entry["chosen"], entry["flags"], entry["match"] = own_pick(path, length, is_hook, self.ep.animal,
                                                                    entry["search"]["plan"], check=self.checks(is_hook))
        return True


def own_pick(path: Path, length: float, is_hook: bool, animal: str, plan: dict,
             check: bool = True) -> tuple[dict, list[str], int | None]:
    """(chosen, flags, match score) for your own clip or photo. It's always used, but held to the same planned shot
    as stock (match.py): under match.PASS it's flagged. A hook clip gets its best window for motion and the hook
    rules (the animal moving, no logo or intro). The score is None when Gemini couldn't look at it."""
    chosen = {"source": "own", "kind": "photo" if path.suffix.lower() in IMAGE_EXTS else "video", "file": str(path),
              "page": "", "author": "you", "licence": "your own media", "licence_url": ""}
    flags = []
    scan = None
    if is_hook and chosen["kind"] == "video":
        scan = hook.scan(path, length)
        chosen.update(start=scan.start, hook=scan.to_json())
        if scan.reject:
            flags.append(f"your hook clip: {scan.reject}")
    elif is_hook:
        flags.append("your hook is a photo: rule 1 wants the animal in motion")
    start = scan.start if scan else clip_start(path, length)
    if not check:  # shorts.json footage.check: Gemini does not look at this beat
        return chosen, flags, None
    try:
        m = match.check(path, animal, plan["shot"], plan.get("key_objects", []), start, length)
    except Exception as e:
        flags.append(f"your clip wasn't checked against the planned shot ({type(e).__name__}: Gemini unavailable)")
        return chosen, flags, None
    chosen.update(check=m["score"], problem=m.get("problem", ""), seen=m.get("seen", ""), focus=[m["x"], m["y"]],
                  **match.evidence(m))
    if scan and not scan.reject:
        hook.judged(scan, m)
        if scan.reject:
            flags.append(f"your hook clip: {scan.reject}")
    if m["score"] < match.PASS:
        missing = f" (no {', '.join(m['missing'])})" if m.get("missing") else ""
        flags.append(f"your clip: shot match {m['score']}/10{missing} for \"{plan['shot']}\": {m.get('seen', '')}")
    return chosen, flags, m["score"]


def _entry(scene, plan: dict) -> dict:
    return {"scene": scene.n, "query": plan["queries"][0] if plan["queries"] else "", "alt_query": "",
            "subject": "", "kind": "footage", "card": lf.local_card(scene), "chosen": None, "alternatives": [],
            "flags": [], "match": None,
            "search": {"plan": plan, "simpler": None, "attempts": [], "skipped": [], "deferred": []}}


def _finish(p: Picker, entry: dict, scene, best: dict | None, length: float) -> None:
    """Use the best attempt, flagged when it's below the match bar, else a placeholder card."""
    plan = entry["search"]["simpler"] or entry["search"]["plan"]
    if best and best["score"] >= match.GENERIC_MAX:
        entry["chosen"] = full(best["_pick"])
        entry["match"] = best["score"]
        if best["score"] < match.PASS:
            missing = f" (no {', '.join(best['missing'])})" if best["missing"] else ""
            entry["flags"].append(f"needs your own clip: the best stock match is {best['score']}/10{missing} for "
                                  f"\"{plan['shot']}\"")
    else:
        if best:
            p.release(best["_pick"])
        entry["chosen"] = lf.make_card(entry, scene, p.out, p.cfg, p.ep.script.lang)
        entry["match"] = 0
        entry["flags"].append(f"needs your own clip: nothing in stock shows \"{plan['shot']}\"; a placeholder card "
                              "is shown")
    others = [a for a in entry["search"]["attempts"] if a.get("_pick") and a is not best and a["score"] is not None
              and a["score"] >= match.PASS and not a["reject"]]
    entry["alternatives"] = [a["_pick"] for a in others][:3]


def full(pick: dict) -> dict:
    """The chosen clip at full quality (it was judged on its preview; the window and framing carry over)."""
    if pick.get("kind") != "video" or not pick.get("preview") or pick.get("source") in ("own", *PLACEHOLDERS):
        return pick
    try:
        return {**pick, "file": str(lf.fetch(pick))}
    except (requests.RequestException, OSError, ValueError, RuntimeError):
        return pick  # the preview stays: a softer picture beats none


def _clean_log(entry: dict) -> None:
    """The search log without the picks' working copies (they're in chosen / alternatives)."""
    s = entry["search"]
    s["attempts"] = [{k: v for k, v in a.items() if k != "_pick"} for a in s["attempts"]]
    s["deferred"] = [{"key": lf.key(m), "page": m.get("page", ""), "query": q, "source": src,
                      "used_in": [u.label() for u in uses]} for m, src, q, uses in s["deferred"]]


def choose(ep, tl, media: Path, out: Path, cfg: dict, log=print) -> list[dict]:
    """footage.json's entries for a Short (see the module notes)."""
    out.mkdir(parents=True, exist_ok=True)
    name_animal(ep, log)
    log(f"      animal: {ep.animal}")
    p = Picker(ep, tl, media, out, cfg, Registry(OUTPUT_DIR, ep.script.slug), log)
    if p.skipped_sources:
        log(f"      ! skipped: {'; '.join(p.skipped_sources)}")
    plans = queries.plan(ep, log)
    scenes = ep.script.scenes
    entries = [_entry(s, plan) for s, plan in zip(scenes, plans)]
    best: dict[int, dict | None] = {}

    def first_pass(i: int) -> None:
        scene, slot, entry = scenes[i], tl.slots[i], entries[i]
        if p.own(entry, scene, slot.length, i == 0) or (plans[i]["reuse_opening"] and i > 0):
            return
        best[i] = p.search(plans[i], slot.length, i == 0, CHECKS, entry["search"])

    with ThreadPoolExecutor(3) as pool:
        list(pool.map(first_pass, range(len(scenes))))

    # nothing matched: a simpler shot stock likely has, searched the same way
    failing = [i for i in best if not best[i] or best[i]["score"] < match.PASS]
    if failing:
        seen = lambda i: (f"{best[i]['score']}/10, {best[i]['seen']}" if best[i] else "nothing usable")
        alt = queries.simpler(ep, [(plans[i], seen(i)) for i in failing], log)

        def second_pass(i: int) -> None:
            if (i + 1) not in alt:
                return
            entries[i]["search"]["simpler"] = alt[i + 1]
            again = p.search(alt[i + 1], tl.slots[i].length, i == 0, SIMPLER_CHECKS, entries[i]["search"])
            if again and (not best[i] or again["score"] > best[i]["score"]):
                if best[i]:
                    p.release(best[i]["_pick"])
                best[i] = again
            elif again:
                p.release(again["_pick"])

        with ThreadPoolExecutor(3) as pool:
            list(pool.map(second_pass, failing))

    # last resort for other beats: a clip another Short used lately, flagged
    for i in [i for i in best if i > 0 and (not best[i] or best[i]["score"] < match.PASS)]:
        plan = entries[i]["search"]["simpler"] or plans[i]
        for m, source, q, used in entries[i]["search"]["deferred"][:RECENT_TRIES]:
            if not p.claim(m):
                continue
            a = p.try_clip(m, plan, tl.slots[i].length, False, q, source)
            a["recent"] = [u.label() for u in used]
            entries[i]["search"]["attempts"].append(a)
            if a["score"] is not None and a["score"] >= match.PASS:
                if best[i]:
                    p.release(best[i]["_pick"])
                best[i] = a
                entries[i]["flags"].append(f"reused: this clip is also in {', '.join(a['recent'])} (nothing "
                                           "unused matched)")
                break
            p.release(m)

    if p.filtered:
        log(f"      {p.filtered} stock results skipped: not tagged as a {ep.animal_search}")
    for i in best:
        _finish(p, entries[i], scenes[i], best[i], tl.slots[i].length)
    for i, (entry, plan) in enumerate(zip(entries, plans)):
        if entry["chosen"] is None and plan["reuse_opening"]:  # cuts back to the opening shot
            entry["chosen"] = dict(entries[0]["chosen"])
            entry["match"] = entries[0]["match"]
            entry["reuses_opening"] = True
    for entry in entries:
        _clean_log(entry)
        lf._thumb(Path(entry["chosen"]["file"]), out / f"scene-{entry['scene']:02d}.jpg",
                  entry["chosen"].get("start", 0.0) + 0.5 if entry["chosen"]["kind"] == "video" else None)
        c = entry["chosen"]
        log(f"      beat {entry['scene']}: {c['source']} {c.get('id', '')}"
            + (f" {entry['match']}/10" if entry["match"] is not None else "")
            + (" (the opening shot)" if entry.get("reuses_opening") else "")
            + (f" [simpler: {entry['search']['simpler']['shot']}]" if entry["search"]["simpler"] else "")
            + (f"  ! {'; '.join(entry['flags'])}" if entry["flags"] else ""))
    return entries


def placeholders(entries: list[dict]) -> list[int]:
    """The beats showing a card instead of footage."""
    return [e["scene"] for e in entries if e["chosen"]["source"] in PLACEHOLDERS]


def weak(entries: list[dict]) -> list[int]:
    """The beats whose clip doesn't show the planned shot well enough (under match.PASS): stock or yours alike. Your
    clip that Gemini couldn't check (no score) isn't counted as weak."""
    return [e["scene"] for e in entries
            if not (e["chosen"]["source"] == "own" and e.get("match") is None) and (e.get("match") or 0) < match.PASS]
