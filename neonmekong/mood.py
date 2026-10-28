"""Mood grades and lyric styles for the lyric video (and its 9:16 Short), chosen per song in song.json.

A grade is a cheap per-frame colour treatment of the picture (before the lyrics, so the text stays clean); a lyric
style says how a line arrives and is sung on screen. Both are keyed by name so the web page can list them.
"""
import cv2
import numpy as np

GRADES = {
    "neon": "Neon (as drawn)",
    "warm": "Warm film",
    "cool": "Cool night",
    "cinema": "Cinema (teal & orange, bars)",
    "dream": "Dream glow",
    "vhs": "VHS tape",
    "mono": "Black & white",
    "cyberpunk": "Cyberpunk (magenta & cyan)",
    "golden": "Golden hour",
    "pastel": "Soft pastel",
    "noir": "Film noir",
    "vintage": "Vintage 8mm",
    "ice": "Ice blue",
    "teal": "Teal & orange",
}
# words in a song's mood, genre and scene idea -> the grade they point to (the first match with most hits wins)
GRADE_WORDS = {
    "cyberpunk": ("cyberpunk", "synthwave", "neon", "futuristic", "electronic", "edm", "nightclub", "club", "robot"),
    "golden": ("sunset", "golden", "summer", "sunrise", "warm", "hopeful", "joyful", "happy", "sunny"),
    "pastel": ("dreamy", "soft", "cute", "kawaii", "tender", "pastel", "sweet", "lullaby", "innocent", "j-pop", "jpop"),
    "noir": ("noir", "detective", "jazz", "smoky", "mystery", "black and white", "monochrome"),
    "vintage": ("nostalgic", "nostalgia", "retro", "vintage", "memory", "memories", "80s", "70s", "90s", "disco",
                "bittersweet", "wistful", "polaroid"),
    "ice": ("cold", "winter", "frozen", "ice", "lonely", "loneliness", "empty", "isolation", "space", "distance"),
    "teal": ("epic", "cinematic", "dramatic", "anthem", "heroic", "rock", "movie"),
    "cool": ("sad", "melancholic", "melancholy", "heartbreak", "grief", "longing", "moody", "dark", "rain"),
    "dream": ("psych", "psychedelic", "hazy", "floating", "ethereal", "dream pop", "trippy", "shoegaze", "lo-fi", "lofi"),
    "vhs": ("glitch", "vhs", "static", "signal", "tape", "rewind", "replay", "analog"),
    "warm": ("romantic", "love", "cozy", "campfire", "acoustic"),
}
STYLE_WORDS = {
    "karaoke": ("karaoke", "singalong", "sing-along", "anthem", "k-pop", "kpop", "j-pop", "jpop", "party"),
    "kinetic": ("hip hop", "hip-hop", "rap", "phonk", "trap", "drill", "edm", "dance", "hype", "energetic", "rock",
                "punk", "upbeat", "electronic"),
    "minimal": ("lofi", "lo-fi", "ambient", "acoustic", "piano", "chill", "soft", "minimal", "ballad", "lullaby"),
}
# The beat effect: on each beat the picture brightens and pushes in a little, and chorus lines glow more.
PULSE_LEVELS = {"off": "Off (no beat effect)", "subtle": "Subtle", "medium": "Medium", "strong": "Strong (club)"}
PULSE_AMOUNT = {"off": (0.0, 0.0), "subtle": (0.035, 0.006), "medium": (0.07, 0.012), "strong": (0.12, 0.02)}  # light, zoom
PULSE_PARTS = {"light": "Brightness", "zoom": "Push-in zoom", "glow": "Lyric glow"}
PULSE_WHEN = {"always": "Every beat", "chorus": "Chorus only"}
DEFAULT_PULSE = "subtle"
PULSE_WORDS = {
    "off": ("ambient", "lullaby", "sleep", "meditat", "piano", "acoustic", "ballad"),
    "medium": ("pop", "upbeat", "funk", "disco", "synthwave", "hip hop", "hip-hop", "groove"),
    "strong": ("edm", "dance", "rock", "punk", "hype", "energetic", "phonk", "trap", "drill", "party", "club"),
}


def pulse_settings(data: dict) -> tuple[float, float, frozenset, str]:
    """(brightness, zoom, which parts beat, "always" or "chorus") for a song's beat effect."""
    level = pick(data.get("beat_pulse"), PULSE_LEVELS, DEFAULT_PULSE)
    parts = data.get("pulse_parts")
    chosen = frozenset(x.strip() for x in str(parts).split(",") if x.strip() in PULSE_PARTS) if parts else frozenset(PULSE_PARTS)
    light, zoom = PULSE_AMOUNT[level]
    return light, zoom, chosen if level != "off" else frozenset(), pick(data.get("pulse_when"), PULSE_WHEN, "always")


LYRIC_STYLES = {
    "classic": "Classic (fade in, neon glow)",
    "karaoke": "Karaoke (the line fills as it is sung)",
    "kinetic": "Kinetic (pops in, kicks on the beat)",
    "minimal": "Minimal (small, lower third)",
}
DEFAULT_GRADE, DEFAULT_STYLE = "neon", "classic"
SAT = {"cyberpunk": 1.35, "golden": 1.15, "pastel": 0.82, "vintage": 0.8, "ice": 0.88, "teal": 1.12}
BAR = 0.105   # cinema's letterbox bars, a fraction of the height each


def pick(name: str | None, allowed: dict, default: str) -> str:
    return name if name in allowed else default


class Grader:
    """grade(frame, t, p): the frame (BGR uint8, edited in place and returned) in the mood; p is the beat pulse."""

    def __init__(self, name: str, size: tuple[int, int]):
        self.name = pick(name, GRADES, DEFAULT_GRADE)
        self.W, self.H = size
        x = np.arange(256, dtype=np.float32) / 255.0
        lut = lambda f: np.clip(f(x) * 255.0, 0, 255).astype(np.uint8)  # noqa: E731
        self.sat, self.grain = SAT.get(self.name, 1.0), self.name in ("vintage", "noir")
        if self.grain:   # a few frames of grain, cycled: noise on every frame would be slow for no gain
            rng = np.random.default_rng(7)
            self.noise = [rng.normal(0, 7 if self.name == "vintage" else 9, (self.H, self.W, 1)).astype(np.float32)
                          for _ in range(4)]
        if self.name == "warm":   # B, G, R curves: lifted shadows, golden highlights
            self.luts = [lut(lambda v: 0.04 + v * 0.86), lut(lambda v: 0.02 + v * 0.95), lut(lambda v: v * 1.06 + 0.01)]
        elif self.name == "cool":
            self.luts = [lut(lambda v: v * 1.08 + 0.02), lut(lambda v: v * 0.99), lut(lambda v: v * 0.88)]
        elif self.name == "cinema":   # teal shadows, orange highlights with an S curve
            s = lambda v: v * v * (3 - 2 * v) * 0.35 + v * 0.65  # noqa: E731
            self.luts = [lut(lambda v: s(v) * 0.92 + (1 - v) * 0.07), lut(lambda v: s(v) * 0.98 + (1 - v) * 0.02),
                         lut(lambda v: s(v) * 1.04 - (1 - v) * 0.03 + v * 0.02)]
        elif self.name == "cyberpunk":   # magenta highlights, cyan-blue shadows
            self.luts = [lut(lambda v: 0.06 + v * 0.92), lut(lambda v: v * 0.8), lut(lambda v: v * v * 0.4 + v * 0.8)]
        elif self.name == "golden":
            self.luts = [lut(lambda v: v * 0.68), lut(lambda v: v * 0.95 + 0.04), lut(lambda v: v * 1.1 + 0.07)]
        elif self.name == "pastel":   # lifted blacks, a little pink and blue
            self.luts = [lut(lambda v: 0.15 + v * 0.8), lut(lambda v: 0.12 + v * 0.78), lut(lambda v: 0.16 + v * 0.8)]
        elif self.name == "noir":   # a hard S curve
            s2 = lambda v: np.clip((v - 0.5) * 1.35 + 0.5, 0, 1)  # noqa: E731
            self.luts = [lut(s2)] * 3
        elif self.name == "vintage":   # faded blacks, warm and slightly green
            self.luts = [lut(lambda v: 0.09 + v * 0.74), lut(lambda v: 0.07 + v * 0.84), lut(lambda v: 0.05 + v * 0.9)]
        elif self.name == "ice":
            self.luts = [lut(lambda v: v * 1.1 + 0.04), lut(lambda v: v * 1.0 + 0.01), lut(lambda v: v * 0.82)]
        elif self.name == "teal":
            s3 = lambda v: v * v * (3 - 2 * v) * 0.3 + v * 0.7  # noqa: E731
            self.luts = [lut(lambda v: s3(v) * 0.9 + (1 - v) * 0.09), lut(lambda v: s3(v) * 0.97 + (1 - v) * 0.03),
                         lut(lambda v: s3(v) * 1.06 - (1 - v) * 0.05 + v * 0.03)]
        else:
            self.luts = None
        yy = np.arange(self.H)
        self.scan = np.where(yy % 4 < 2, 1.0, 0.82).astype(np.float32)[:, None, None]
        self.vignette = None
        if self.name in ("cinema", "dream", "vhs", "noir", "vintage"):
            gx, gy = np.meshgrid(np.linspace(-1, 1, self.W, dtype=np.float32), np.linspace(-1, 1, self.H, dtype=np.float32))
            self.vignette = (1.0 - 0.38 * np.clip(gx * gx * 0.6 + gy * gy, 0, 1.4))[..., None]

    def grade(self, frame: np.ndarray, t: float, p: float = 0.0) -> np.ndarray:
        n = self.name
        if n == "neon":
            return frame
        if self.luts:
            b, g, r = cv2.split(frame)
            frame = cv2.merge([cv2.LUT(b, self.luts[0]), cv2.LUT(g, self.luts[1]), cv2.LUT(r, self.luts[2])])
        if self.sat != 1.0:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[..., 1] = np.clip(hsv[..., 1] * self.sat, 0, 255)
            frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        if n == "noir":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        if self.grain:
            frame = np.clip(frame.astype(np.float32) + self.noise[int(t * 12) % 4], 0, 255).astype(np.uint8)
        if n == "mono":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(cv2.convertScaleAbs(gray, alpha=1.12, beta=-6), cv2.COLOR_GRAY2BGR)
        elif n == "dream":   # a soft bloom of the bright parts, breathing with the beat
            small = cv2.resize(frame, (self.W // 6, self.H // 6), interpolation=cv2.INTER_AREA)
            bloom = cv2.GaussianBlur(small, (0, 0), 6)
            bloom = cv2.resize(bloom, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            frame = cv2.addWeighted(frame, 0.82, bloom, 0.45 + 0.2 * p, 6)
        elif n == "vhs":   # scanlines, a red/blue split, a slow rolling band
            sh = max(2, self.W // 400)
            frame[..., 2] = np.roll(frame[..., 2], sh, axis=1)
            frame[..., 0] = np.roll(frame[..., 0], -sh, axis=1)
            frame = (frame.astype(np.float32) * self.scan).astype(np.uint8)
            y = int((t * 0.12 % 1.0) * self.H)
            band = slice(y, min(y + max(4, self.H // 40), self.H))
            frame[band] = cv2.add(frame[band], np.full_like(frame[band], 14))
        if self.vignette is not None:
            frame = (frame.astype(np.float32) * self.vignette).astype(np.uint8)
        if n == "cinema":
            h = int(self.H * BAR)
            frame[:h] = 0
            frame[self.H - h:] = 0
        return frame


def ease_out_back(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def pop_scale(t: float, start: float, beat_pulse: float, chorus: bool) -> float:
    """Kinetic style: a line lands at 1.28x and settles over 0.32 s; chorus lines also kick on the beat."""
    u = (t - (start - 0.1)) / 0.32
    land = 1.28 - 0.28 * ease_out_back(u) if u < 1 else 1.0
    return land + (0.05 * beat_pulse if chorus else 0.0)


def fill_fraction(t: float, start: float, end: float) -> float:
    """Karaoke style: how much of the line has been sung (eased, so the wipe leads the voice a little)."""
    if end <= start:
        return 1.0
    return min(max((t - start + 0.05) / (end - start), 0.0), 1.0)


def scaled(sp: dict, s: float) -> dict:
    """The sprite resized by `s` (premultiplied colour, alpha and glow together)."""
    if abs(s - 1.0) < 0.01:
        return sp
    w, h = max(int(sp["w"] * s), 2), max(int(sp["h"] * s), 2)
    rs = lambda a: cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR).reshape(h, w, -1)  # noqa: E731
    return {**sp, "pm": rs(sp["pm"]), "a": rs(sp["a"]), "glow": rs(sp["glow"]), "w": w, "h": h}


def cut(sp: dict, rows: list[tuple[int, int, int, int]], fraction: float) -> list[tuple[dict, int, int]]:
    """Karaoke: the sprite's parts that are lit at `fraction` of the line, as (part sprite, x, y offset in the sprite). `rows` are each text row's (top, bottom, left, right) in the sprite; the wipe runs row by row."""
    out = []
    pos = fraction * len(rows)
    for i, (y0, y1, x0, x1) in enumerate(rows):
        f = min(max(pos - i, 0.0), 1.0)
        if f <= 0:
            continue
        x_to = x0 + max(int((x1 - x0) * f), 1)
        part = {"pm": sp["pm"][y0:y1, x0:x_to], "a": sp["a"][y0:y1, x0:x_to], "glow": sp["glow"][y0:y1, x0:x_to],
                "w": x_to - x0, "h": y1 - y0}
        out.append((part, x0, y0))
    return out



def _hits(text: str, words: tuple[str, ...]) -> list[str]:
    import re

    return [w for w in words if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text)]


def suggest(data: dict) -> dict:
    """The mood grade and lyric style that fit the song, from the words of its mood, genre and scene
    idea (the mood and genre count double: they describe the song itself): {grade, style, pulse, reason}.
    `reason` reads "melancholic, synthwave song"."""
    song = f"{data.get('mood_phrase') or ''} {data.get('genre') or ''}".lower()
    text = f"{song} {data.get('scene_theme') or ''}".lower()

    def best(table: dict, default: str) -> str:
        score = {k: len(_hits(text, w)) + len(_hits(song, w)) for k, w in table.items()}
        top = max(score.values(), default=0)
        return max(score, key=score.get) if top > 0 else default

    def picks(table: dict, limit: int) -> list[str]:
        score = {k: len(_hits(text, w)) + len(_hits(song, w)) for k, w in table.items()}
        return [k for k, v in sorted(score.items(), key=lambda kv: -kv[1]) if v > 0][:limit]

    words = _hits(song, tuple(dict.fromkeys(w for t in (GRADE_WORDS, STYLE_WORDS) for ws in t.values()
                                            for w in ws)))
    found = [w for w in words if not any(w != o and w in o for o in words)][:3]
    return {"grade": best(GRADE_WORDS, DEFAULT_GRADE), "style": best(STYLE_WORDS, DEFAULT_STYLE),
            "pulse": best(PULSE_WORDS, DEFAULT_PULSE), "reason": (", ".join(found) + " song") if found else "song"}
