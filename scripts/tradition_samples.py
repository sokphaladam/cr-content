"""Draw the sample pictures the Lyrics page shows for each art tradition (frontend/public/traditions/<key>.webp).

The same scene and seed in every tradition, drawn the way a song's pictures are (traditions.apply/avoid over the
anime model), so the samples show the real difference. Run again after changing a tradition's prompt:
    python scripts/tradition_samples.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from crcontent import imagegen  # noqa: E402
from neonmekong import traditions  # noqa: E402

SCENE = "a girl with headphones sitting by a window, a small town and the sky outside, evening"
OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "traditions"
SEED = 1234


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key in traditions.TRADITIONS:
        negative = ", ".join(x for x in (traditions.avoid(key), "text, watermark, logo") if x)
        picture = imagegen.generate(traditions.apply(SCENE, key), "anime", (1920, 1080), seed=SEED, negative=negative)
        im = Image.open(picture).convert("RGB")
        im.thumbnail((480, 480))
        im.save(OUT / f"{key or 'default'}.webp", quality=82)
        print("drew", key or "default")


if __name__ == "__main__":
    main()
