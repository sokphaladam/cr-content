"""Local AI scene art: Stable Diffusion XL on this computer's NVIDIA GPU, free after a one-time model download.

Each look uses its own SDXL model (downloaded the first time that look is used, ~7 GB, into <ROOT>/models):
anime (Animagine XL 4.0), cinematic (RealVisXL 5) and flat 2D motion-graphics (SDXL base). Pictures are drawn at
SDXL's native size for the frame's shape, then a second "hi-res" pass redraws them HIRES_SCALE x bigger so they stay crisp
at 1080p (fx.py moves the camera over them). Results are cached by prompt, look, size and seed.

Only one model sits on the GPU at a time; call unload() when a job is done so lyric timing (Whisper) has room.
"""
import hashlib
import os
import threading
from pathlib import Path

from .config import CACHE_DIR, ROOT

MODELS_DIR = ROOT / "models"
GEN_CACHE = CACHE_DIR / "gen"
VAE_REPO = "madebyollin/sdxl-vae-fp16-fix"  # the stock SDXL VAE overflows (black images) in half precision
_DIFFUSERS_FILES = ["model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "text_encoder/*",
                    "text_encoder_2/*", "unet/*", "vae/*"]

# prompt: how a scene description is wrapped for that model (it was trained on that kind of caption)
STYLES: dict[str, dict] = {
    "anime": {
        "label": "Anime illustration",
        "repo": "cagliostrolab/animagine-xl-4.0",
        "variant": None,
        # quality tags first: the text encoder reads only ~75 tokens, and whatever comes after that is dropped
        "prefix": "masterpiece, high score, great score, absurdres, ",
        "suffix": ", anime screencap, cinematic lighting",
        "negative": "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, "
                    "worst quality, low quality, low score, bad score, average score, signature, watermark, username, "
                    "blurry, jpeg artifacts, logo, letters",
        "steps": 26, "cfg": 5.0, "scheduler": "euler_a",
    },
    "cinematic": {
        "label": "Cinematic realistic",
        "repo": "SG161222/RealVisXL_V5.0",
        "variant": "fp16",
        "prefix": "cinematic film still, ",
        "suffix": ", shot on 35mm, shallow depth of field, dramatic lighting, color graded, highly detailed, 8k",
        "negative": "(worst quality, low quality, illustration, 3d, 2d, painting, cartoons, sketch), text, watermark, "
                    "logo, letters, signature, deformed, disfigured, bad anatomy, extra limbs, blurry, open mouth",
        "steps": 25, "cfg": 4.5, "scheduler": "dpmpp_2m_karras",
    },
    "flat": {
        "label": "Flat 2D motion graphics",
        "repo": "stabilityai/stable-diffusion-xl-base-1.0",
        "variant": "fp16",
        "prefix": "flat vector illustration, ",
        "suffix": ", clean geometric shapes, bold limited color palette, smooth gradients, minimalist, motion graphics "
                  "style, dribbble, behance, high quality",
        "negative": "photo, photorealistic, 3d render, text, letters, watermark, logo, signature, noisy, blurry, "
                    "low quality, cluttered, messy lines",
        "steps": 28, "cfg": 7.0, "scheduler": "dpmpp_2m_karras",
    },
}

_lock = threading.RLock()
_pipe = None  # the loaded text-to-image pipeline
_pipe_style = ""
_idle: threading.Timer | None = None
IDLE_UNLOAD_SEC = 180
# unload() moves the model to system memory instead of dropping it: copying it back to the GPU takes a few seconds,
# reading 7 GB from disk again takes up to a minute on a hard drive. Dropped for good after PARK_SEC unused.
_parked = None
_parked_style = ""
_park_timer: threading.Timer | None = None
PARK_SEC = 900
HIRES_SCALE = 1.5  # ~38 s a picture on an RTX 3060, 7.8 GB of video memory at most


def gpu_name() -> str:
    """The CUDA GPU's name, or "" when there is none (or torch isn't installed)."""
    try:
        import torch

        return torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""
    except Exception:
        return ""


def installed() -> bool:
    """torch and diffusers can be imported (the desktop app needs its AI add-on for that, see addons.py)."""
    try:
        import diffusers  # noqa: F401
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def _model_dir(style: str) -> Path:
    return MODELS_DIR / STYLES[style]["repo"].split("/")[-1]


def downloaded(style: str) -> bool:
    """Every part's weights are on disk (folders and configs arrive first, so they prove nothing)."""
    root = _model_dir(style)
    if not (root / "model_index.json").exists():
        return False
    return all(any((root / part).glob("*.safetensors")) for part in ("unet", "text_encoder", "text_encoder_2", "vae"))


def _patterns(style: str) -> list[str]:
    """Which files of the model repo to fetch."""
    spec = STYLES[style]
    if spec["variant"]:  # only the half-precision weights (the repo also has full-precision ones), plus configs
        return ["model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "*/config.json",
                f"*/*.{spec['variant']}.safetensors"]
    return _DIFFUSERS_FILES


def _expected_bytes(style: str) -> int:
    """Total size of the files download() fetches, asked from Hugging Face once and remembered next to the model."""
    import fnmatch
    import json

    note = _model_dir(style) / ".download-size.json"
    try:
        return int(json.loads(note.read_text())["bytes"])
    except Exception:
        pass
    from huggingface_hub import HfApi

    patterns = _patterns(style)
    total = sum(getattr(f, "size", 0) or 0 for f in HfApi().list_repo_tree(STYLES[style]["repo"], recursive=True)
                if any(fnmatch.fnmatch(f.path, p) for p in patterns))
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(json.dumps({"bytes": total}))
    return total


# downloads running in this process: style -> {"transfer": bar, "files": bar} (tqdm bars fed by huggingface_hub)
_live: dict[str, dict] = {}


def _tracker(style: str):
    """A silent tqdm class for snapshot_download that keeps its bars in _live, so progress() can read the exact
    bytes received and the speed while they arrive (the files on disk only grow in big bursts)."""
    import io

    from tqdm.auto import tqdm

    bars = _live[style] = {}

    class Bar(tqdm):
        def __init__(self, *args, **kwargs):
            kwargs.pop("name", None)
            desc = str(kwargs.get("desc", ""))
            kwargs.update(file=io.StringIO(), disable=False, mininterval=0.2)
            super().__init__(*args, **kwargs)
            # huggingface_hub makes a network-bytes bar, a bytes-written bar (its total = what's left to fetch)
            # and a files bar
            kind = "transfer" if desc.startswith("Downloading") else "written" if desc.startswith("Reconstruct") else "files"
            bars[kind] = self

    return Bar


def _live_progress(style: str) -> dict | None:
    bars = _live.get(style)
    if not bars or "transfer" not in bars or "written" not in bars:
        return None
    transfer, written = bars["transfer"], bars["written"]
    try:
        expected = _expected_bytes(style)
    except Exception:
        expected = 0
    left = int(written.total or 0)  # bytes this run has to fetch; the rest was already on disk
    got = min(int(transfer.n), left) if left else int(transfer.n)
    total = max(expected, left)
    rate = transfer.format_dict.get("rate") or 0
    return {"done": total - left + got, "total": total, "active": True, "speed": int(rate),
            "eta": int((left - got) / rate) if rate and left > got else None}


def progress(style: str) -> dict | None:
    """How far a download has got: {"done", "total"} in bytes, whether it is moving, and (for a download this
    process runs) "speed" in bytes/s and "eta" in seconds. None when nothing has been fetched yet. Other
    downloads (another process) are measured from the files on disk, finished and partial (*.incomplete)."""
    import time

    live = _live_progress(style)
    if live:
        return live
    root = _model_dir(style)
    if not root.exists():
        return None
    done, active = 0, False
    for f in root.rglob("*"):
        if not f.is_file() or f.name.startswith(".download-size"):
            continue
        st = f.stat()
        if f.suffix == ".incomplete":
            done += st.st_size
            active = active or time.time() - st.st_mtime < 90
        elif ".cache" not in f.parts:
            done += st.st_size
    try:
        total = _expected_bytes(style)
    except Exception:  # offline: show what we have without a percentage
        total = 0
    return {"done": done, "total": max(total, done), "active": active}


def status() -> dict:
    """What the Settings page shows: is the GPU usable, which looks are downloaded, and download progress."""
    styles = {}
    for k, v in STYLES.items():
        ready = downloaded(k)
        styles[k] = {"label": v["label"], "downloaded": ready, "progress": None if ready else progress(k)}
    return {"installed": installed(), "gpu": gpu_name(), "styles": styles, "folder": str(MODELS_DIR)}


def download(style: str, log=print) -> Path:
    """Fetch a look's model (and the shared VAE) once; later calls return straight away."""
    from huggingface_hub import snapshot_download

    spec = STYLES[style]
    target = _model_dir(style)
    vae = MODELS_DIR / "sdxl-vae-fp16-fix"
    if not (vae / "config.json").exists():
        snapshot_download(VAE_REPO, local_dir=vae, allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"])
    if not downloaded(style):
        log(f"      downloading the {spec['label'].lower()} model (about 7 GB, first time only)...")
        try:
            snapshot_download(spec["repo"], local_dir=target, allow_patterns=_patterns(style),
                              tqdm_class=_tracker(style))
        finally:
            _live.pop(style, None)
        log("      model downloaded")
    return target


def _scheduler(pipe, name: str):
    from diffusers import DPMSolverMultistepScheduler, EulerAncestralDiscreteScheduler

    if name == "euler_a":
        return EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    return DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True,
                                                   algorithm_type="dpmsolver++")


def _load(style: str, log=print):
    global _pipe, _pipe_style, _parked, _parked_style
    if _pipe is not None and _pipe_style == style:
        return _pipe
    import torch
    from diffusers import AutoencoderKL, StableDiffusionXLPipeline

    if not torch.cuda.is_available():
        raise RuntimeError("AI scene art needs an NVIDIA GPU with CUDA (none was found).")
    unload()
    spec = STYLES[style]
    if _parked is not None and _parked_style == style:
        log(f"      moving the {spec['label'].lower()} model back onto the GPU")
        pipe = _parked
        _parked, _parked_style = None, ""
        pipe.to("cuda")
    else:
        drop_parked()  # another look: free its memory before reading this one
        path = download(style, log)
        log(f"      loading the {spec['label'].lower()} model onto the GPU")
        # weights go straight from the files to the GPU, not through a full copy in system memory first
        vae = AutoencoderKL.from_pretrained(MODELS_DIR / "sdxl-vae-fp16-fix", torch_dtype=torch.float16,
                                            device_map="cuda")
        pipe = StableDiffusionXLPipeline.from_pretrained(
            path, vae=vae, torch_dtype=torch.float16, use_safetensors=True, device_map="cuda",
            **({"variant": spec["variant"]} if spec["variant"] else {}))
        pipe.scheduler = _scheduler(pipe, spec["scheduler"])
        pipe.set_progress_bar_config(disable=True)
        pipe.vae.enable_tiling()  # the hi-res pass decodes ~1.2k x 1.8k images; tiles keep it inside 12 GB
    _pipe, _pipe_style = pipe, style
    return pipe


def unload() -> None:
    """Free the GPU. The model waits in system memory for PARK_SEC, so the next picture of that look starts fast."""
    global _pipe, _pipe_style, _idle, _parked, _parked_style, _park_timer
    with _lock:
        if _idle:
            _idle.cancel()
            _idle = None
        if _pipe is None:
            return
        pipe, style = _pipe, _pipe_style
        _pipe, _pipe_style = None, ""
        import gc

        import torch

        try:
            pipe.to("cpu")
            _parked, _parked_style = pipe, style
            if _park_timer:
                _park_timer.cancel()
            _park_timer = threading.Timer(PARK_SEC, drop_parked)
            _park_timer.daemon = True
            _park_timer.start()
        except Exception:  # not enough system memory: just drop it
            _parked, _parked_style = None, ""
        del pipe
        gc.collect()
        torch.cuda.empty_cache()


def drop_parked() -> None:
    """Forget the model unload() kept in system memory."""
    global _parked, _parked_style, _park_timer
    with _lock:
        if _park_timer:
            _park_timer.cancel()
            _park_timer = None
        if _parked is None:
            return
        _parked, _parked_style = None, ""
        import gc

        gc.collect()


def unload_later(seconds: float = IDLE_UNLOAD_SEC) -> None:
    """Free the GPU once no picture has been drawn for `seconds` (drawing scene by scene keeps the model warm)."""
    global _idle
    if _idle:
        _idle.cancel()
    _idle = threading.Timer(seconds, unload)
    _idle.daemon = True
    _idle.start()


def default_seed(prompt: str) -> int:
    """The seed a prompt gets when none is chosen: the same prompt always gives the same picture."""
    return int(hashlib.sha1(prompt.strip().encode()).hexdigest()[:8], 16)


def base_size(size: tuple[int, int]) -> tuple[int, int]:
    """SDXL's native resolution for a frame shape (~1 megapixel, multiples of 64)."""
    W, H = size
    if W > H:
        return 1216, 832
    if W < H:
        return 832, 1216
    return 1024, 1024


_MALE = {"1boy", "2boys", "3boys", "multiple boys", "male focus", "mature male", "old man"}
_FEMALE = {"1girl", "2girls", "3girls", "multiple girls", "female focus", "mature female", "old woman"}


def _sexes(prompt: str) -> tuple[bool, bool]:
    tags = {t.strip().lower() for t in prompt.split(",")}
    return bool(tags & _MALE), bool(tags & _FEMALE)


def full_prompt(prompt: str, style: str) -> str:
    spec = STYLES[style]
    prompt = prompt.strip().rstrip(",")
    male, female = _sexes(prompt)
    if style == "anime" and male and not female and "male focus" not in prompt.lower():
        # without it Animagine draws "1boy" with long or messy hair as a girl (and pastes any beard onto her)
        head, _, rest = prompt.partition(",")
        prompt = f"{head}, male focus,{rest}" if rest else f"{head}, male focus"
    return f"{spec['prefix']}{prompt}{spec['suffix']}"


def _sex_negative(prompt: str, style: str) -> str:
    """Keep an anime man from turning into a girl, and keep beards off women."""
    if style != "anime":
        return ""
    male, female = _sexes(prompt)
    if male and not female:
        return "1girl, female, breasts, feminine, makeup, lipstick"
    if female and not male:
        return "facial hair, mustache, beard, stubble"
    return ""


def cache_file(prompt: str, style: str, size: tuple[int, int], seed: int, hires: bool = True, negative: str = "") -> Path:
    """Where generate() keeps this picture (it may not be drawn yet)."""
    w, h = base_size(size)
    # the full prompt and hi-res scale are part of the key, so changing a look's wording draws new pictures
    key = hashlib.sha1(f"{style}\n{w}x{h}\n{seed}\n{hires}{HIRES_SCALE}\n{negative}{_sex_negative(prompt, style)}\n"
                       f"{full_prompt(prompt.strip(), style)}"
                       .encode()).hexdigest()[:16]
    return GEN_CACHE / f"{style}-{key}.png"


def drawn(prompt: str, style: str, size: tuple[int, int], seed: int) -> Path | None:
    """The picture if generate() already drew it, else None (nothing is drawn)."""
    if style not in STYLES or not prompt.strip():
        return None
    out = cache_file(prompt, style, size, seed)
    return out if out.exists() and out.stat().st_size else None


def generate(prompt: str, style: str, size: tuple[int, int], seed: int | None = None, hires: bool = True,
             negative: str = "", log=print) -> Path:
    """One picture of `prompt` in a look from STYLES, shaped for a frame of `size` (it's cropped to fit later).

    `seed` fixes the result (the same seed and prompt give the same picture); None derives one from the prompt.
    `hires`: redraw HIRES_SCALE x bigger for detail (about twice as slow). Cached: the same request comes straight back.
    """
    if style not in STYLES:
        raise ValueError(f"Unknown art style {style!r}")
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Say what the picture should show.")
    w, h = base_size(size)
    if seed is None:
        seed = default_seed(prompt)
    out = cache_file(prompt, style, size, seed, hires, negative)
    if out.exists() and out.stat().st_size:
        return out
    with _lock:
        import torch
        from diffusers import StableDiffusionXLImg2ImgPipeline

        spec = STYLES[style]
        pipe = _load(style, log)
        neg = ", ".join(x for x in (spec["negative"], _sex_negative(prompt, style), negative) if x)
        generator = torch.Generator("cuda").manual_seed(seed)
        image = pipe(prompt=full_prompt(prompt, style), negative_prompt=neg, width=w, height=h,
                     num_inference_steps=spec["steps"], guidance_scale=spec["cfg"], generator=generator).images[0]
        if hires:
            # the same modules, not from_pipe(): that made a second copy of the model (14 GB on a 12 GB card)
            refine = StableDiffusionXLImg2ImgPipeline(**pipe.components)
            refine.set_progress_bar_config(disable=True)
            image = image.resize((round(w * HIRES_SCALE / 8) * 8, round(h * HIRES_SCALE / 8) * 8), resample=3)  # bicubic
            image = refine(prompt=full_prompt(prompt, style), negative_prompt=neg, image=image, strength=0.38,
                           num_inference_steps=max(spec["steps"], 20), guidance_scale=spec["cfg"],
                           generator=generator).images[0]
        GEN_CACHE.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".part.png")
        image.save(tmp)
        os.replace(tmp, out)
    return out
