"""Channel profiles (HIDDEN-HISTORY-FILES-SHORTS-IMPLEMENTATION-SPEC.md section 4): one production engine, several
channels with their own editorial defaults. A profile sets defaults for a new Script-to-Video project (visual style,
target length, voice direction...); it never forks the editor or the renderer. A project records the profile's id and
version (DirectorPlan.project.channel_profile_id / _version, and its output meta.json). A project with no id, like
every project made before profiles, keeps the general defaults it always had; an unknown id falls back to them with
a warning, it never fails.
"""
from pydantic import BaseModel, Field

from .styles import CaptionStyle, available_fonts

SCHEMA = 1  # this file's profile schema; a profile written for a newer schema is not loaded


class Format(BaseModel):
    format: str = "short"
    aspect_ratio: str = "9:16"
    target_seconds: float = 0
    fps: int = 30


class ChannelProfile(BaseModel):
    id: str
    display_name: str
    description: str = ""
    version: int = Field(ge=1)
    schema_version: int = SCHEMA
    format_defaults: Format = Field(default_factory=Format)
    visual_style: str
    palette: dict[str, str] = {}      # role -> hex colour
    caption_style: str = ""
    font_preferences: list[str] = []  # first installed one wins; the app's fonts are the fallback
    voice_defaults: str = ""          # direction for the voice, not a voice id
    music_mood: str = ""
    sound_design_defaults: list[str] = []
    story_rules: list[str] = []
    research_rules: list[str] = []
    footage_priority: list[str] = []
    preflight_rules: dict[str, str] = {}  # check -> severity
    metadata_defaults: dict[str, str] = {}
    # the theme a new project starts from (styles.CaptionStyle fields); {} = the general caption look
    caption_defaults: dict[str, str | int | float] = {}
    caption_font_preferences: list[str] = []  # first installed one wins; none = the language's caption font
    headline_font_preferences: list[str] = []


PROFILES: dict[str, ChannelProfile] = {p.id: p for p in (
    ChannelProfile(
        id="wildlife_facts", display_name="Wildlife Facts", version=1,
        description="Animal facts: the animal on screen, in motion, from the first frame.",
        visual_style="cinematic_wildlife",
        palette={"background": "#101722", "accent": "#FFC857", "text": "#F8FAFC", "keyword": "#42C7D9",
                 "secondary": "#246B78"},
        caption_defaults={"preset": "bold", "size": "l", "color": "#F8FAFC", "highlight": "#FFC857",
                          "keyword": "#42C7D9", "outline": "outline", "case": "as_is", "headline_color": "#F8FAFC",
                          "headline_background": "#10202B", "hook_fill": "#FFC857"},
        caption_font_preferences=["Inter", "Montserrat"],
        headline_font_preferences=["Anton", "Bebas Neue", "Montserrat"],
        sound_design_defaults=["crisp natural ambience", "subtle impacts on meaningful actions", "restrained whooshes"],
        voice_defaults="warm, curious, quick", music_mood="curious, light",
        story_rules=["hook with the animal doing the surprising thing", "one fact per beat", "natural loop to the start"],
        footage_priority=["user_media", "species_footage", "licensed_stock"],
    ),
    ChannelProfile(
        id="hidden_history_files", display_name="Hidden History Files", version=1,
        description="Source-backed history mysteries: archive, artifacts and maps, cinematic documentary look.",
        format_defaults=Format(target_seconds=40), visual_style="cinematic_history",
        palette={"background": "#101419", "accent": "#B99A60", "text": "#D6C9AC", "keyword": "#76AFA7",
                 "headline": "#F0E8D8", "secondary": "#315C60", "danger": "#B45D52"},
        caption_defaults={"preset": "minimal", "size": "m", "color": "#D6C9AC", "highlight": "#B99A60",
                          "keyword": "#76AFA7", "outline": "shadow", "case": "as_is", "headline_color": "#F0E8D8",
                          "headline_background": "#101419", "hook_fill": "#B99A60"},
        caption_font_preferences=["Inter", "Montserrat"],
        headline_font_preferences=["Bebas Neue", "Anton", "Cormorant Garamond", "Montserrat"],
        font_preferences=["Bebas Neue", "Anton", "Inter", "Montserrat", "Cormorant Garamond"],
        voice_defaults="measured, curious, authoritative; not horror-trailer delivery",
        music_mood="low restrained ambience", sound_design_defaults=["impacts only on real story beats"],
        story_rules=["hook (0-3s): surprising evidence, consequence or specific question; no channel intro",
                     "context (3-10s): who, where and when",
                     "investigation (10-25s): clues, records, artifacts or conflicting explanations",
                     "revelation (25-40s): what the evidence actually shows",
                     "resonance: why it matters or what remains uncertain"],
        research_rules=["central claims need at least one directly relevant credible source",
                        "dates, numbers, quotes, named people and causes must be explicitly supported",
                        "Wikipedia is never the sole evidence for a central claim",
                        "record disagreements; never invent dates, quotes, places or consensus"],
        footage_priority=["user_media", "archive", "museum", "wikimedia", "licensed_stock", "ai_reconstruction"],
        preflight_rules={"unsupported_central_claim": "blocked", "rights_unknown": "review_required",
                         "unlabelled_reconstruction": "blocked"},
        metadata_defaults={"credits_heading": "Sources and visual credits"},
    ),
)}


def theme_captions(profile: ChannelProfile | None, lang: str) -> CaptionStyle:
    """A new project's CaptionStyle from `profile`: its caption_defaults over the general defaults, and the first
    of its preferred fonts installed for `lang` (Khmer only lists Khmer-capable fonts, so a Latin brand face never
    lands on Khmer text). None -> the general CaptionStyle, unchanged."""
    if profile is None:
        return CaptionStyle()
    known = CaptionStyle.model_fields.keys() - {"font", "headline_font"}
    try:
        style = CaptionStyle(**{k: v for k, v in profile.caption_defaults.items() if k in known})
    except ValueError:  # a bad value in a profile never stops a project from being made
        style = CaptionStyle()
    fonts = available_fonts(lang)
    style.font = next((f for f in profile.caption_font_preferences if f in fonts), "")
    style.headline_font = next((f for f in profile.headline_font_preferences if f in fonts), "")
    return style.clean(lang)


def resolve(profile_id: str) -> tuple[ChannelProfile | None, str]:
    """(profile, warning). "" -> (None, ""): the general defaults. An unknown id -> (None, a warning)."""
    if not profile_id:
        return None, ""
    found = PROFILES.get(profile_id)
    if found is None or found.schema_version > SCHEMA:
        return None, f"Channel profile {profile_id!r} isn't known to this app, so the general defaults are used."
    return found, ""


def stamp(meta: dict, plan) -> dict:
    """Copy a plan's profile into an output's meta.json dict (nothing for a project without one)."""
    pid = getattr(getattr(plan, "project", None), "channel_profile_id", "")
    if pid:
        found = PROFILES.get(pid)
        meta.update(channel_profile_id=pid, channel_profile_version=plan.project.channel_profile_version,
                    channel_profile_name=found.display_name if found else pid)
    return meta
