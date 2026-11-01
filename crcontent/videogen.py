"""Image-to-video on this computer's GPU (LTX-Video 0.9.5 through diffusers): a still picture brought to life with real
motion in it (a character nodding, writing, steam rising), following a prompt. Used for the animated cover's
"Character motion" (coverloop.animate).

The picture is pinned as the first frame; coverloop.repeat plays the take forward then backward, so it repeats with
no seam. Fits a 12 GB card with the text encoder kept in system RAM (model CPU offload): a 4-second take
at 768x448 is a few minutes on an RTX 3060. The model is ~24 GB, downloaded once into <data folder>/models.
"""
from pathlib import Path

from .imagegen import MODELS_DIR

REPO = "Lightricks/LTX-Video-0.9.5"
DIR = MODELS_DIR / "ltx-video-0.9.5"
PATTERNS = ["model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*", "transformer/*", "vae/*"]
SIZE = (768, 448)   # 16:9-ish, both multiples of 32 (what the model needs); upscaled to the video's size afterwards
FRAMES = 97         # 8k + 1 frames: 4 s at 24 fps
FPS = 24
STEPS = 40
GUIDANCE = 3.0
NEGATIVE = "worst quality, inconsistent motion, blurry, jittery, distorted, deformed face, extra fingers, morphing, text"


def settings() -> dict:
    """What a take is made with (saved beside the loop, so a good one can be made again). No motion strength: tried
    as partial denoising from the still picture, 0.9.5 then barely moves at all (40 and 70 alike)."""
    return {"model": REPO, "size": list(SIZE), "frames": FRAMES, "fps": FPS, "steps": STEPS, "guidance": GUIDANCE}


def downloaded() -> bool:
    return (DIR / "model_index.json").exists() and any((DIR / "transformer").glob("*.safetensors"))


def check() -> None:
    """ValueError saying what's missing (the download itself happens on first use)."""
    from . import imagegen

    if not imagegen.installed():
        raise ValueError("Character motion needs the AI add-on: Settings → AI features → Install AI add-on.")
    if imagegen.device() != "cuda":
        raise ValueError("Character motion needs an NVIDIA graphics card.")


def download(log=print) -> Path:
    from huggingface_hub import snapshot_download

    if not downloaded():
        log("Downloading the video model (about 24 GB, first time only)…")
        snapshot_download(REPO, local_dir=DIR, allow_patterns=PATTERNS)
    return DIR


def cover_crop(picture: Path, size: tuple[int, int]):
    """The picture scaled to cover `size` and centre-cropped, as a PIL image."""
    from PIL import Image

    im = Image.open(picture).convert("RGB")
    w, h = size
    k = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * k)), max(h, round(im.height * k))), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def take(picture: Path, prompt: str, out: Path, seed: int = 0, log=print, progress=None) -> Path:
    """One 4-second take of `picture` moving as `prompt` says, starting on the picture, as an mp4 at SIZE.
    progress(step, steps) while it is drawn.

    Run in a process of its own: the model's ~24 GB in system RAM is only all given back when that process ends
    (in the engine, the next take ran out of memory), and a crash inside torch ends that process, not the engine.
    RuntimeError when it fails."""
    import multiprocessing as mp
    import queue

    ctx = mp.get_context("spawn")   # a fresh interpreter: nothing of the engine's GPU state carried over
    messages = ctx.Queue()
    child = ctx.Process(target=_child, args=(str(picture), prompt, str(out), seed, messages), daemon=True)
    child.start()
    error = ""
    while True:
        try:
            kind, *value = messages.get(timeout=1)
        except queue.Empty:
            if not child.is_alive():
                break
            continue
        if kind == "log":
            log(value[0])
        elif kind == "progress" and progress:
            progress(*value)
        elif kind == "error":
            error = value[0]
        elif kind == "done":
            break
    child.join()
    if error or child.exitcode != 0 or not Path(out).exists():
        raise RuntimeError(error or f"The video model stopped unexpectedly (exit code {child.exitcode}): usually "
                                    "too little free memory. Close other big apps and make it again.")
    return Path(out)


def _child(picture: str, prompt: str, out: str, seed: int, messages) -> None:
    """take() inside its own process: what it says goes back through `messages`."""
    from . import addons

    addons.activate()   # the desktop app's torch lives in the AI add-on
    try:
        _take(Path(picture), prompt, Path(out), seed, lambda t: messages.put(("log", str(t))),
              lambda i, n: messages.put(("progress", i, n)))
        messages.put(("done",))
    except Exception as e:
        messages.put(("error", (str(e).strip().splitlines() or [repr(e)])[-1][-300:]))


def _take(picture: Path, prompt: str, out: Path, seed: int, log, progress) -> Path:
    """take()'s work, in the process it runs in."""
    image = cover_crop(picture, SIZE)   # an unreadable picture fails here, before 24 GB is loaded
    import torch
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXConditionPipeline, LTXVideoCondition
    from diffusers.utils import export_to_video

    import gc

    download(log)
    # the text encoder (9 GB) on its own first, then gone before the video model loads: the two together are what
    # ran the computer out of memory (a native crash, exit code 0xC0000005)
    log("Reading the movement…")
    reader = LTXConditionPipeline.from_pretrained(DIR, transformer=None, vae=None, torch_dtype=torch.bfloat16)
    try:
        reader.text_encoder.to("cuda")   # straight onto the card: offload hooks kept a second copy in RAM (+10 GB)
        with torch.no_grad():
            embeds = reader.encode_prompt(prompt, NEGATIVE, do_classifier_free_guidance=True, device=torch.device("cuda"))
    finally:
        del reader
        gc.collect()
        torch.cuda.empty_cache()
    log("Loading the video model onto the GPU…")
    pipe = LTXConditionPipeline.from_pretrained(DIR, text_encoder=None, tokenizer=None, torch_dtype=torch.bfloat16)
    try:
        pipe.enable_model_cpu_offload()
        pipe.vae.enable_tiling()          # decoding 97 frames at once doesn't fit 12 GB otherwise
        # first frame only: pinned last too, 0.9.5 stays frozen and then morphs back in the final ~16 frames
        conditions = [LTXVideoCondition(image=image, frame_index=0)]

        def step(_pipe, i, _t, kw):
            if progress:
                progress(i + 1, STEPS)
            return kw

        log("Drawing the motion…")
        frames = pipe(conditions=conditions, prompt_embeds=embeds[0], prompt_attention_mask=embeds[1],
                      negative_prompt_embeds=embeds[2], negative_prompt_attention_mask=embeds[3], width=SIZE[0], height=SIZE[1],
                      num_frames=FRAMES, frame_rate=FPS, num_inference_steps=STEPS, guidance_scale=GUIDANCE,
                      decode_timestep=0.05, decode_noise_scale=0.025,
                      generator=torch.Generator("cuda").manual_seed(seed), callback_on_step_end=step).frames[0]
        export_to_video(frames, str(out), fps=FPS)
    finally:
        pipe.remove_all_hooks()   # the offload hooks form cycles: without this + gc the memory stays in system RAM
        del pipe
        gc.collect()
        torch.cuda.empty_cache()
    return out
