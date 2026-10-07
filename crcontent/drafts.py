"""Drafts: scripts being edited, stored on disk as drafts/<id>/draft.json (one folder per draft)."""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from .config import DRAFTS_DIR
from .script import VideoScript


class Draft(BaseModel):
    script: VideoScript
    lang: str = "en"
    topic: str = ""
    voice: str = ""
    rate: str = "+5%"
    music: str = ""
    created: str = ""
    updated: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _folder(draft_id: str) -> Path:
    folder = (DRAFTS_DIR / draft_id).resolve()
    if folder.parent != DRAFTS_DIR.resolve() or not draft_id or draft_id.startswith("."):
        raise KeyError(draft_id)
    return folder


def _write(folder: Path, draft: Draft) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "draft.json.tmp"
    tmp.write_text(draft.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, folder / "draft.json")  # atomic: a crash never leaves a half-written draft


def create(draft: Draft) -> tuple[str, Draft]:
    draft_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
    draft.created = draft.updated = _now()
    _write(_folder(draft_id), draft)
    return draft_id, draft


def save(draft_id: str, draft: Draft) -> Draft:
    folder = _folder(draft_id)
    if not (folder / "draft.json").exists():
        raise KeyError(draft_id)
    draft.created = load(draft_id).created or _now()
    draft.updated = _now()
    _write(folder, draft)
    return draft


def load(draft_id: str) -> Draft:
    path = _folder(draft_id) / "draft.json"
    if not path.exists():
        raise KeyError(draft_id)
    return Draft.model_validate_json(path.read_text(encoding="utf-8"))


def delete(draft_id: str) -> None:
    folder = _folder(draft_id)
    if not (folder / "draft.json").exists():
        raise KeyError(draft_id)
    for f in folder.iterdir():
        f.unlink()
    folder.rmdir()


def list_drafts() -> list[dict]:
    if not DRAFTS_DIR.exists():
        return []
    items = []
    for folder in DRAFTS_DIR.iterdir():
        path = folder / "draft.json"
        if not path.is_file():
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # skip a damaged file rather than breaking the whole list
        script = d.get("script") or {}
        scenes = script.get("scenes") or []
        items.append({
            "id": folder.name,
            "title": script.get("title") or d.get("topic") or "Untitled draft",
            "lang": d.get("lang", "en"),
            "updated": d.get("updated", ""),
            "scenes": len(scenes),
            "cover": next((s.get("media") for s in scenes if s.get("media")), ""),
        })
    return sorted(items, key=lambda x: x["updated"], reverse=True)


def import_rendered_videos(output_dir: Path) -> list[tuple[str, list[str]]]:
    """Create a draft from each rendered video's script.json (videos are left untouched).

    Identical scripts in the same language become one draft. Each video's meta.json gets a "draft" link.
    Videos already linked to an existing draft are skipped. Returns [(draft_id, [video folders])].
    """
    groups: dict[str, dict] = {}
    for folder in sorted(output_dir.iterdir()):
        script_path, meta_path = folder / "script.json", folder / "meta.json"
        if not script_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        if meta.get("draft") and (DRAFTS_DIR / meta["draft"] / "draft.json").exists():
            continue
        script = VideoScript.load(script_path)
        lang = meta.get("lang") or ("km" if "-km-" in folder.name else "en")
        key = lang + "|" + script.model_dump_json()
        created = meta.get("created") or datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds")
        g = groups.setdefault(key, {"script": script, "lang": lang, "meta": meta, "folders": [], "created": created})
        g["folders"].append(folder)
        if created >= g["created"]:  # settings of the most recent render win
            g["meta"], g["created"] = meta, created

    results = []
    for g in groups.values():
        draft = Draft(script=g["script"], lang=g["lang"], topic=g["meta"].get("topic", ""),
                      voice=g["meta"].get("voice", ""))
        draft_id, _ = create(draft)
        # keep the library order meaningful: date the draft by its latest render
        draft.created = draft.updated = g["created"]
        _write(_folder(draft_id), draft)
        for folder in g["folders"]:
            meta_path = folder / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            meta.setdefault("lang", g["lang"])
            meta["draft"] = draft_id
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append((draft_id, [f.name for f in g["folders"]]))
    return results
