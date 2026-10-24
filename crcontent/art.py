"""Gemini as art director: it draws scene backgrounds and designs complete covers as SVG, which resvg rasterizes.

Backgrounds are full-bleed artwork with no text (render_scene gives them a slow push-in, like any photo), or animated
with SMIL as a seamless looping clip (motion.py plays the animation frame by frame into an mp4). Covers are
a whole layout around a photo of the video (gradients, panels, badges, the headline set in real type); Gemini then
looks at its own render once and fixes whatever reads badly at thumbnail size.
"""
import base64
import hashlib
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import llm

from .config import CACHE_DIR, LLM_MODEL, LANGS
from .script import make_client
from .styles import available_fonts, font_dirs

ART_CACHE = CACHE_DIR / "art"
PHOTO = "PHOTO"  # href Gemini gives the cover's photo; swapped for the real picture at render time

# families resvg can find (system / user / assets fonts), offered to Gemini for headlines
COVER_FONTS = {
    "en": ["Impact", "Arial Black", "Segoe UI Black", "Bahnschrift", "Georgia", "Trebuchet MS", "Verdana", "Arial"],
    "km": [],  # filled from styles.available_fonts("km") at call time
}

# shared by the still and the animated art direction
CRAFT = """- Pick a deliberate palette of 3-5 colours that carries the mood; strong value contrast; one accent colour.
- Simple, bold shapes read better than fine detail. Stylised illustration, abstract, geometric or cinematic light
  all work; avoid trying to draw photorealistic people or faces.
- Reply with exactly one complete <svg> element and nothing else: no markdown fences, no commentary."""

ART_SYSTEM = """You are the art director and illustrator for short-form videos (YouTube Shorts, TikTok, Reels) and
music videos. You draw with SVG code: the SVG you write is rendered as a still picture by resvg (a strict, static
SVG 1.1 renderer with most of SVG 2 painting).

What works in resvg: linearGradient, radialGradient (with fx/fy, spreadMethod), patterns, clipPath, mask, opacity,
mix-blend-mode, isolation, all of feGaussianBlur / feTurbulence / feColorMatrix / feComponentTransfer /
feDisplacementMap / feBlend / feComposite / feMorphology / feDropShadow / feOffset / feFlood / feMerge / feTile,
transforms, paths, text with font-family, font-weight, letter-spacing, text-anchor, paint-order, stroke on text.
What doesn't: scripts, animation (<animate>, CSS animation), <foreignObject>, CSS @import or web fonts, external
files or URLs, textLength-based auto fitting (text never wraps or shrinks by itself: you place every line).

Craft:
- Look like a professional designer made it, not clip art. Layer depth: a rich background (multi-stop gradients,
  soft blurred light blooms, subtle texture or film grain from feTurbulence at low opacity), a clear focal element,
  and atmosphere (haze, glow, light rays, bokeh, vignette).
""" + CRAFT

MOTION_LOOP_SEC = 6.0
MOTION_SYSTEM = """You are the motion designer for short-form videos (YouTube Shorts, TikTok, Reels) and music
videos. You animate with SVG code: the SVG you write is played frame by frame. At each frame its SMIL animations are
evaluated and the picture is rendered by resvg (a strict SVG 1.1 renderer with most of SVG 2 painting); the frames
become a seamless looping video clip of exactly {loop:g} seconds.

Animation that works:
- <animate attributeName=".." values="a;b;a" dur=".." repeatCount="indefinite"/>, with keyTimes, and
  calcMode="spline" + keySplines for easing (use keySplines="0.42 0 0.58 1" per segment for organic motion), or
  calcMode="discrete"; also from/to and <set>.
- <animateTransform attributeName="transform" type="translate|scale|rotate|skewX|skewY" values=".." additive="sum"/>
  (additive="sum" stacks it on the element's own transform; several animateTransforms on one element must all be
  additive="sum"). Put an animation inside the element it moves, or point at it with href="#id".
- Any number or colour can move: cx, cy, r, x, y, width, height, opacity, fill-opacity, stroke-dashoffset, fill,
  stop-color, stop-opacity, offset, gradient x1/y1/x2/y2/cx/cy/r/fx/fy, gradientTransform, path d (same commands and
  number count in every value), points, stdDeviation, feColorMatrix values, feDisplacementMap scale.
What doesn't work: CSS animation, @keyframes or transitions, <animateMotion>, event begins (click, x.end), scripts,
<foreignObject>, external files, web fonts. An animated property must be an attribute, not inside style="".

The loop must be seamless:
- every animation has repeatCount="indefinite" and a dur that divides {loop:g}s evenly (e.g. {choices})
- every values list ends on the value it starts with (values="0;40;0"), or turns fully (rotate 0 to 360)
- stagger with a negative begin (begin="-2s"), never a positive delay

Paint the still picture first (as good as a still would be), then bring it to life:
- slow, cinematic, ambient motion: drifting light blooms, gradients that breathe and shift hue, floating particles
  or bokeh rising, slow parallax between layers, light rays sweeping, rippling waves, a glow pulsing, stars
  twinkling. Layers moving at different speeds give depth. Move things by 2-10% of the frame per loop.
- nothing flashes, strobes or jumps; keep it calm enough to sit behind words for the whole clip.
- every frame is rendered from scratch, and filters are what makes that slow. Draw glows, blooms, bokeh and haze
  as shapes filled with a radialGradient that fades to stop-opacity 0: it looks the same as a blur and costs
  nothing. Use feGaussianBlur only where a gradient can't do it, on single small shapes, stdDeviation 20 at most,
  never on a group or layer that spans the frame. No feTurbulence anywhere (film grain is added afterwards). At
  most about 80 animated elements.

Craft:
- Look like a professional designer made it, not clip art. Layer depth: a rich background (multi-stop gradients,
  soft blurred light blooms), a clear focal element, and atmosphere (haze, glow, light rays, bokeh, vignette).
""".format(loop=MOTION_LOOP_SEC, choices=", ".join(f"{MOTION_LOOP_SEC / k:g}s" for k in (1, 2, 3, 4, 6))) + CRAFT

BACKGROUND_TASK = """Draw a background for one moment of a video. It sits behind white captions and moves with a slow
zoom, so:
- full-bleed, edge to edge, {w}x{h} (viewBox="0 0 {w} {h}"), no borders or frames
- NO text, letters, numbers, logos or watermarks anywhere
- keep the band from about 30% to 75% of the height calm and mid-to-dark so white captions read on top; put the
  brightest light and detail toward the top or edges
- it should feel like it belongs to a premium, cinematic video, and clearly evoke the subject below

The moment:
<subject>
{subject}
</subject>"""

MOTION_TASK = """Animate a background for one moment of a video. It loops behind white captions, so:
- full-bleed, edge to edge, {w}x{h} (viewBox="0 0 {w} {h}"), no borders or frames; anything that moves must keep
  the frame covered at every moment (oversize moving layers so no edge ever shows)
- NO text, letters, numbers, logos or watermarks anywhere
- keep the band from about 30% to 75% of the height calm and mid-to-dark so white captions read on top in every
  frame; put the brightest light and the busiest motion toward the top or edges
- it should feel like it belongs to a premium, cinematic video, and clearly evoke the subject below

The moment:
<subject>
{subject}
</subject>"""

COVER_TASK = """Design the cover (thumbnail) of a {kind}. Size {w}x{h} (viewBox="0 0 {w} {h}"), seen tiny in a feed.

The picture: an <image href="PHOTO" x=".." y=".." width=".." height=".." preserveAspectRatio="xMidYMid slice"/>
shows the photo you are given (use href="PHOTO" exactly; it is replaced by the real picture). Make it big and let
it be the hero: you may crop it into a shape, give it a duotone or colour grade with filters, frame it, split the
layout, or run it full-bleed under gradients. Keep the subject of the photo visible.

The headline, exactly these words: {text}
Highlight these word(s) in the accent colour: {emphasis}
{direction}
Typography rules:
- fonts available (font-family must be one of these): {fonts}
- this is the most important element: huge and heavy; it must read at 15% size. Set each line yourself with its own
  <text> (or <tspan x=".." dy="..">); nothing wraps automatically.
- size every line so it fits inside the frame with at least {margin}px on every side. Estimate width as
  characters x font-size x {char_w} for this script; when in doubt make the text smaller or use more lines.
- give the text contrast with the photo: a thick dark stroke with paint-order="stroke", a solid panel or band
  behind it, a strong drop shadow, or a gradient scrim.
{safe}
Add designer polish that suits the subject: a glow, colour blocks, a badge or tag, an arrow or circle pointing at
something in the photo, light leaks, grain. Every element must earn its place; no clutter, no fake UI, no emoji,
no other words than the headline (a small badge of 1-2 words is fine when it adds punch, e.g. NEW, PART 2, a year).

About the {kind}:
{about}"""

REVIEW_TASK = """This is your cover, rendered at thumbnail size. Check it hard, like a picky art director:
- is any text cut off at the edge, overlapping the wrong thing, or running outside the frame?
- is the headline readable at a glance (size, contrast, stroke)? are the highlighted words clearly in the accent colour?
- is the photo's subject still visible, and does it look polished and professional?
If it is already good, reply with just OK. Otherwise reply with the complete corrected <svg> and nothing else."""


def _client(client: llm.Client | None) -> llm.Client:
    return client or make_client()


def _ask(client: llm.Client, content: list[dict], max_tokens: int = 16000, effort: str = "medium",
         system: str = ART_SYSTEM) -> str:
    response = client.beta.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        output_config={"effort": effort},
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Gemini declined to draw this.")
    return "".join(b.text for b in response.content if b.type == "text")


_SVG = re.compile(r"<svg\b.*</svg>", re.S | re.I)


def clean_svg(reply: str) -> str:
    """The <svg> in Gemini's reply, with anything that could reach outside the picture removed: scripts, foreign
    objects, and links to anything but its own elements, inline data, or the photo placeholder."""
    match = _SVG.search(reply)
    if not match:
        raise RuntimeError("Gemini's reply had no SVG in it.")
    svg = match.group(0)
    svg = re.sub(r"<(script|foreignObject)\b.*?</\1\s*>|<(script|foreignObject)\b[^>]*/>", "", svg, flags=re.S | re.I)
    svg = re.sub(r"@import[^;]*;", "", svg)

    def link(m: re.Match) -> str:
        value = m.group(3)
        ok = value.startswith("#") or value == PHOTO or value.startswith("data:image/")
        return m.group(0) if ok else ""

    svg = re.sub(r"""\s(xlink:href|href)\s*=\s*(["'])(.*?)\2""", link, svg, flags=re.S)
    svg = re.sub(r"url\(\s*(?!['\"]?#)[^)]*\)", "none", svg)  # url(...) may only point at the SVG's own defs
    if "xmlns=" not in svg[:300]:
        svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    if PHOTO in svg and "xmlns:xlink" not in svg[:400]:
        svg = svg.replace("<svg", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
    return svg


def _font_dirs() -> list[str]:
    return [str(d) for d in font_dirs()]


def rasterize(svg: str, size: tuple[int, int], out: Path, photo: Path | None = None) -> Path:
    """Render `svg` to `out` (.png, or .jpg through ffmpeg) at `size`; `photo` fills the PHOTO placeholder."""
    import resvg_py

    if PHOTO in svg:
        if photo is None:
            raise ValueError("This design needs a photo.")
        mime = "image/png" if photo.suffix.lower() == ".png" else "image/jpeg"
        uri = f"data:{mime};base64," + base64.b64encode(photo.read_bytes()).decode()
        svg = re.sub(r"""(href\s*=\s*["'])PHOTO(["'])""", lambda m: m.group(1) + uri + m.group(2), svg)
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=size[0], height=size[1], font_dirs=_font_dirs(),
                                      font_family="Arial", sans_serif_family="Arial"))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".png":
        out.write_bytes(png)
        return out
    tmp = out.with_suffix(".render.png")
    tmp.write_bytes(png)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-q:v", "2", str(out)],
                       stdin=subprocess.DEVNULL, capture_output=True, check=True)
    finally:
        tmp.unlink(missing_ok=True)
    return out


def _png_block(png: Path) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                        "data": base64.b64encode(png.read_bytes()).decode()}}


def _jpeg_block(data: bytes) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(data).decode()}}


# ---------- backgrounds ----------

def background(subject: str, size: tuple[int, int], client: llm.Client | None = None) -> Path:
    """Gemini-drawn artwork for `subject` (the scene's narration, search words, the song's mood...), as a PNG at
    `size`. The same subject and size come back from the cache instead of being drawn again."""
    subject = subject.strip()[:1500]
    if not subject:
        raise ValueError("Say what the background should show.")
    W, H = size
    key = hashlib.sha1(f"{W}x{H}\n{subject}".encode()).hexdigest()[:16]
    out = ART_CACHE / f"bg-{key}.png"
    if out.exists() and out.stat().st_size:
        return out
    task = BACKGROUND_TASK.format(w=W, h=H, subject=subject)
    if W > H:
        task = task.replace("band from about 30% to 75% of the height", "lower third")
    svg = clean_svg(_ask(_client(client), [{"type": "text", "text": task}]))
    out.with_suffix(".svg").parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".svg").write_text(svg, encoding="utf-8")
    # twice the frame size: render_scene zooms into stills, and this keeps the push-in sharp
    return rasterize(svg, (W * 2, H * 2), out)


def motion_background(subject: str, size: tuple[int, int], client: llm.Client | None = None,
                      log=print) -> Path:
    """Gemini-animated artwork for `subject`, as an mp4 at `size` that loops seamlessly every MOTION_LOOP_SEC (scenes
    loop video clips to their length). Cached like background(); the SVG is kept next to it."""
    from . import motion

    subject = subject.strip()[:1500]
    if not subject:
        raise ValueError("Say what the background should show.")
    W, H = size
    key = hashlib.sha1(f"motion {W}x{H}\n{subject}".encode()).hexdigest()[:16]
    out = ART_CACHE / f"motion-{key}.mp4"
    if out.exists() and out.stat().st_size:
        return out
    task = MOTION_TASK.format(w=W, h=H, subject=subject)
    if W > H:
        task = task.replace("band from about 30% to 75% of the height", "lower third")
    svg = clean_svg(_ask(_client(client), [{"type": "text", "text": task}], max_tokens=20000, system=MOTION_SYSTEM))
    ART_CACHE.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".svg").write_text(svg, encoding="utf-8")
    return motion.render_loop(svg, size, out, MOTION_LOOP_SEC, log=log)


def try_background(subject: str, size: tuple[int, int], log=print) -> Path | None:
    """background(), or None when Gemini can't draw right now (no key, no credits, offline)."""
    try:
        return background(subject, size)
    except Exception as e:
        log(f"      ! Gemini art unavailable: {type(e).__name__}: {str(e)[:160]}")
        return None


# ---------- covers ----------

def _cover_fonts(lang: str) -> list[str]:
    return available_fonts("km") if lang == "km" else COVER_FONTS["en"]


def design_cover(photo_jpeg: bytes, text: str, emphasis: str, about: str, lang: str, size: tuple[int, int],
                 kind: str = "video", direction: str = "", base_svg: str = "",
                 client: llm.Client | None = None) -> str:
    """An SVG cover template (photo slot href="PHOTO") for the headline `text` around this photo. `direction`: an
    art direction for this cover; `base_svg`: an earlier design to keep while changing only the headline."""
    W, H = size
    client = _client(client)
    profile = LANGS.get(lang, LANGS["en"])
    portrait = H > W
    safe = ("- it's a vertical cover: keep the headline in the upper 60%; the bottom 20% is hidden by the app's buttons "
            "and caption, so nothing important there.") if portrait else ""
    if base_svg:
        ask = (f"Here is a cover you designed earlier:\n{base_svg}\n\nKeep its design (layout, colours, effects, photo "
               f"placement) but change the headline to exactly: {text}\nHighlight: {emphasis or '(none)'}\n"
               f"Re-set the lines so the new words fit with at least {round(W * 0.05)}px margin. Fonts available: "
               f"{', '.join(_cover_fonts(lang))}.")
    else:
        ask = COVER_TASK.format(
            kind=kind, w=W, h=H, text=text, emphasis=emphasis or "(pick the strongest word)",
            direction=f"Art direction for this cover: {direction}\n" if direction else "",
            fonts=", ".join(_cover_fonts(lang)), margin=round(W * 0.05),
            char_w="0.62 (Latin caps in a heavy font)" if lang != "km" else "0.55 per character (Khmer, counting "
                   "every code point; Khmer needs about 1.6x line height for stacked vowels)",
            safe=safe, about=about)
        if lang == "km":
            ask += f"\nThe headline is in {profile.name}: never upper-case it, keep its words exactly."
    content = [{"type": "text", "text": "The photo:"}, _jpeg_block(photo_jpeg), {"type": "text", "text": ask}]
    return clean_svg(_ask(client, content))


def review_cover(svg: str, photo: Path, size: tuple[int, int], workdir: Path,
                 client: llm.Client | None = None) -> str:
    """Gemini looks at its rendered cover once and returns a fixed SVG, or the same one when it's already good."""
    preview = workdir / f"review-{hashlib.sha1(svg.encode()).hexdigest()[:10]}.png"
    W, H = size
    scale = 540 / max(W, H)
    rasterize(svg, (round(W * scale), round(H * scale)), preview, photo)
    try:
        reply = _ask(_client(client), [
            {"type": "text", "text": f"Your SVG:\n{svg}"}, _png_block(preview), {"type": "text", "text": REVIEW_TASK}],
            effort="low")
    finally:
        preview.unlink(missing_ok=True)
    return clean_svg(reply) if "<svg" in reply.lower() else svg


def make_cover(photo: Path, text: str, emphasis: str, about: str, lang: str, size: tuple[int, int], out: Path,
               kind: str = "video", direction: str = "", base_svg: str = "", review: bool = True) -> str:
    """Design, self-review and render one cover to `out` (.jpg). Returns the final SVG template."""
    client = make_client()
    preview = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(photo), "-vf", "scale=512:-2", "-q:v", "4", "-f", "image2",
         "-c:v", "mjpeg", "-"], stdin=subprocess.DEVNULL, capture_output=True, check=True).stdout
    svg = design_cover(preview, text, emphasis, about, lang, size, kind, direction, base_svg, client)
    if review:
        try:
            svg = review_cover(svg, photo, size, out.parent, client)
        except Exception as e:  # the first design still stands
            print(f"  ! cover review: {type(e).__name__}: {e}")
    rasterize(svg, size, out, photo)
    out.with_suffix(".svg").write_text(svg, encoding="utf-8")
    return svg


def make_covers(jobs: list[dict], workers: int = 4) -> list[str | Exception]:
    """make_cover() for several covers at once (each dict holds its keyword arguments); a failed one is returned
    as its exception so the others still count."""
    def one(kw: dict):
        try:
            return make_cover(**kw)
        except Exception as e:
            print(f"  ! designed cover: {type(e).__name__}: {e}")
            return e

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(jobs)))) as pool:
        return list(pool.map(one, jobs))
