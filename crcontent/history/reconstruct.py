"""AI reconstructions for history shots (spec 9, H6).

A shot whose visual_origin is "reconstruction" (something no camera recorded) gets a structured brief built here in
plain code from the APPROVED research only: period, place, the claims its scene states that are supported (verified
details), the disputed / uncertain ones (never drawn as certain), what must not be invented, framing and aspect.
The prompt the generator gets is short (SDXL reads ~75 tokens): what the shot shows, the place and the period. The
creator sees the brief and can edit the prompt before drawing.

Pictures are drawn by the free local generator (imagegen.py, SDXL on this computer); no paid service is needed, and
your own file (shot-003-1.jpg) works too. Every reconstruction picture gets an "AI RECONSTRUCTION" label burnt in, so
the final video can never pass it off as archive material, and is stored as asset_type "reconstruction".
"""
import hashlib
from pathlib import Path

from ..config import CACHE_DIR
from ..director_plan import Footage, Shot

LABEL = "AI RECONSTRUCTION"
OUT = CACHE_DIR / "reconstructions"
STYLE = "cinematic"  # imagegen.STYLES: RealVisXL, photographic
NEGATIVE = ("text, letters, writing, inscription, watermark, logo, signature, modern objects, cars, power lines, "
            "plastic, wristwatch, eyeglasses, sneakers, modern clothing")
NOT_INVENTED = ["readable inscriptions or writing", "named people's faces", "flags, insignia or coats of arms",
                "exact numbers of people, ships or buildings", "architecture or costume details the research doesn't state"]
FRAMING = {"extreme_wide": "extreme wide shot", "wide": "wide shot", "establishing": "establishing wide shot",
           "aerial": "aerial view", "close_up": "close-up", "extreme_close_up": "macro close-up", "medium": "medium shot"}


def brief(plan, shot: Shot, research) -> dict:
    """The reconstruction brief for one shot. Raises ValueError while the research isn't approved."""
    if research is None or research.research_status != "approved":
        raise ValueError("Approve the research first: a reconstruction is drawn only from checked facts.")
    scene = next((s for s in plan.scenes if s.id == shot.scene_id), None)
    claims = {c.id: c for c in research.claims}
    stated = [claims[cid] for cid in (scene.claim_ids if scene else []) if cid in claims]
    place = (research.places or plan.continuity.locations or [""])[0]
    what = shot.visual_description or shot.subject or shot.purpose
    framing = FRAMING.get(shot.camera.angle if shot.camera.angle == "aerial" else shot.shot_type, "")
    verified = [c.claim_text for c in stated if c.status == "supported"]
    prompt = ", ".join(x for x in (what, place, research.period, framing, "historical reconstruction, natural light") if x)
    return {
        "shot_id": shot.id,
        "period": research.period, "location": place,
        "verified": verified,
        "uncertain": [f"{c.claim_text} ({c.status})" for c in stated if c.status in ("disputed", "uncertain")],
        "must_not_invent": NOT_INVENTED,
        "framing": framing, "aspect": plan.project.aspect_ratio,
        "kind": "proposed reconstruction" if verified else "illustrative",
        "research_revision": research.approved_revision,
        "prompt": prompt, "negative": NEGATIVE,
    }


def label(src: Path, out: Path) -> Path:
    """A copy of the picture with the label burnt in, top left, inset so a slow push-in or a 9:16 crop keeps it."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(src).convert("RGB")
    w, h = img.size
    size = max(14, round(min(w, h) * 0.035))
    font = ImageFont.load_default(size=size)
    d = ImageDraw.Draw(img, "RGBA")
    x, y = round(w * 0.18), round(h * 0.12)  # inside the middle of a 16:9 frame cropped to 9:16, and past a 10 % zoom
    l, t, r, b = d.textbbox((x, y), LABEL, font=font)
    pad = round(size * 0.45)
    d.rounded_rectangle((l - pad, t - pad, r + pad, b + pad), radius=pad, fill=(16, 20, 25, 200))
    d.text((x, y), LABEL, font=font, fill=(214, 201, 172, 255))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


def footage(file: Path, b: dict, seed: int | None, author: str) -> Footage:
    return Footage(source="reconstruction", kind="photo", file=str(file), thumb=f"/cache/{OUT.name}/{file.name}",
                   author=author, licence="made by the app", match="drawn", query=b["prompt"],
                   asset_type="reconstruction", depicts="illustrative", rights="licensed",
                   raw={"brief": b, "seed": seed, "label": LABEL})


def draw(b: dict, size: tuple[int, int], seed: int | None = None, log=print) -> Footage:
    """Draw it with the local generator and label it. Raises RuntimeError when the generator isn't installed."""
    from .. import imagegen

    if not imagegen.installed():
        raise RuntimeError("The local image generator isn't installed (Settings → AI add-on). "
                           f"Or add your own picture named {b['shot_id']}.jpg to the media folder.")
    raw = imagegen.generate(b["prompt"], STYLE, size, seed, negative=b["negative"], log=log)
    key = hashlib.sha1(f"{raw.name}{LABEL}".encode()).hexdigest()[:16]
    return footage(label(raw, OUT / f"{key}.jpg"), b, seed, "AI reconstruction (Stable Diffusion XL, on this computer)")


def own(file: Path, shot: Shot) -> Footage:
    """Your own file on a reconstruction shot: a photo gets the label too; a video must carry it already."""
    if file.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv", ".m4v"):
        return Footage(source="own", kind="video", file=str(file), author="you", licence="your own media", match="own",
                       asset_type="reconstruction", depicts="illustrative", rights="licensed")
    key = hashlib.sha1(f"{file}{file.stat().st_mtime_ns}{LABEL}".encode()).hexdigest()[:16]
    f = footage(label(file, OUT / f"{key}.jpg"), {"prompt": ""}, None, "you")
    f.source, f.licence, f.match, f.raw = "own", "your own media", "own", {"label": LABEL, "original": str(file)}
    return f
