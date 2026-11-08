# cr-content — Channel-Branded Visual System

## Goal

Make the visual identity of every video follow its selected **Channel profile**. A Wildlife Facts video and a Hidden History Files video should not look like the same template with different footage.

The selected channel profile should control sensible defaults for:

- Caption font, headline font and typography hierarchy
- Normal caption text, spoken-word highlight and keyword colors
- Scene headline and opening-hook colors
- Caption outline/background treatment and word grouping
- Video color grade and visual atmosphere
- Motion-graphics style and transition rhythm
- Sound-design defaults and music mood
- Lower thirds, maps, source labels and AI-reconstruction labels where relevant

Users must still be able to customize individual projects in the editor. A profile supplies defaults; it must not lock the editor.

**Compatibility rule:** existing drafts, General projects and the current wildlife pipeline must keep their current appearance unless the creator explicitly selects a channel profile for a new project or chooses **Apply channel style**.

---

## 1. Current repository findings

The repository already has the foundation:

- `crcontent/profiles.py` defines `wildlife_facts` and `hidden_history_files`, including palettes, font preferences, sound defaults and editorial rules.
- `crcontent/styles.py` defines `CaptionStyle` with normal text (`color`), spoken word (`highlight`) and keyword (`keyword`) colors.
- `crcontent/captions.py` renders word-timed captions and scene headlines into ASS subtitles.
- `frontend/components/LivePreview.tsx` previews captions and has the `CaptionPanel` controls for fonts and three caption colors.
- `frontend/components/ScriptVideoForm.tsx` lets the creator choose the channel profile.
- `crcontent/web.py` tags new projects with `channel_profile_id` and `channel_profile_version` in `/api/script-video`.
- `frontend/lib/api.ts` has the `ChannelProfile` and `CaptionStyle` TypeScript interfaces.

The missing link is that the channel profile's theme is not currently applied to `script.captions`, and the headline in the preview/render still uses fixed white/black styling. `caption_style` and the profile font preferences are not a complete, working theme system yet.

Relevant files:

- `crcontent/profiles.py`
- `crcontent/styles.py`
- `crcontent/captions.py`
- `crcontent/web.py`
- `frontend/lib/api.ts`
- `frontend/components/ScriptVideoForm.tsx`
- `frontend/components/LivePreview.tsx`
- `tests/test_channel_profiles.py`
- Add focused caption-style tests under `tests/` if no existing test module covers `CaptionStyle`/ASS rendering.

---

## 2. Channel theme defaults

Build the theme around the two existing profiles. Keep the profile registry extensible so future channels can define their own theme without adding `if channel == ...` conditions throughout the renderer.

### A. Wildlife Facts

**Creative direction:** energetic, vivid, clean wildlife-documentary look. The animal should remain the visual hero. Text must be highly readable over bright outdoor footage.

Palette:

| Role | Color |
|---|---|
| Background / dark surface | `#101722` |
| Accent / spoken word | `#FFC857` |
| Main text | `#F8FAFC` |
| Keyword accent | `#42C7D9` |
| Secondary teal | `#246B78` |

Typography preferences (first installed font wins):

- Caption: `Inter`, `Montserrat`, then the language's system font
- Headline: `Anton`, `Bebas Neue`, `Montserrat`
- Khmer: use an installed Khmer-capable font/system fallback; never force a Latin-only headline font on Khmer text

Caption defaults:

```json
{
  "preset": "bold",
  "size": "l",
  "color": "#F8FAFC",
  "highlight": "#FFC857",
  "keyword": "#42C7D9",
  "outline": "outline",
  "case": "as_is",
  "headline_color": "#F8FAFC",
  "headline_background": "#10202B"
}
```

Editing direction:

- Strong, fast but controlled caption pop.
- Thick dark outline for contrast over feathers, sky, forest and water.
- Use one or two highlighted keywords per beat, not every other word.
- Use punchy headline entrances and quick cuts when the animal's behavior supports them.
- Keep the footage color grade natural/vibrant; do not oversaturate animal colors.
- Sound: crisp natural ambience, subtle impacts on meaningful actions, restrained whooshes.

### B. Hidden History Files

**Creative direction:** premium historical documentary / case-file identity. It should feel archival, researched and cinematic—not like a meme, gaming overlay or horror trailer.

Palette:

| Role | Color |
|---|---|
| Background / charcoal | `#101419` |
| Accent / spoken word | `#B99A60` |
| Main text / parchment | `#D6C9AC` |
| Keyword accent / muted teal | `#76AFA7` |
| Headline ivory | `#F0E8D8` |
| Secondary deep teal | `#315C60` |
| Restrained danger / warning | `#B45D52` |

Typography preferences (first installed font wins):

- Caption: `Inter`, `Montserrat`, then the language's system font
- Headline: `Bebas Neue`, `Anton`, `Cormorant Garamond`, `Montserrat`
- Use a strong condensed headline face and a neutral caption face; do not use the decorative serif for small captions.
- Khmer: use an installed Khmer-capable font/system fallback; never force a Latin-only font on Khmer text.

Caption defaults:

```json
{
  "preset": "minimal",
  "size": "m",
  "color": "#D6C9AC",
  "highlight": "#B99A60",
  "keyword": "#76AFA7",
  "outline": "shadow",
  "case": "as_is",
  "headline_color": "#F0E8D8",
  "headline_background": "#101419"
}
```

Editing direction:

- Parchment normal captions, antique-gold spoken word, muted-teal keywords.
- Dark charcoal headline panel with warm ivory text; gold is a restrained accent, not a full-screen glow.
- The opening hook may use the spoken-word accent as its background with dark text for contrast.
- Slow document reveals, map pans, subtle parallax, timeline/date cards and restrained film-grain overlays.
- Use a cinematic/film/mono grade according to the subject, but preserve real archive colors when they carry evidence.
- Sound: low restrained ambience, paper/map/metal details where appropriate, impacts only on real story beats.
- No emoji in documentary headlines. Keep case-file identifiers small and consistent.
- Any AI reconstruction must remain explicitly labelled as a reconstruction. Never visually style it as authentic archive footage.

### C. General / no profile

Do not change current defaults. Existing General videos should continue to use the existing Classic caption preset and current global styling.

---

## 3. Data model changes

### `crcontent/profiles.py`

Extend `ChannelProfile` with explicit, typed theme defaults rather than leaving `caption_style` as an unused string:

- `caption_defaults: dict[str, str | int | float]`
- `caption_font_preferences: list[str]`
- `headline_font_preferences: list[str]`
- Optional future fields for `visual_grade`, `motion_preset`, `transition_preset`, `lower_third_preset`, `sound_design_defaults` and `graphic_theme`.

Keep existing `palette`, `font_preferences`, `caption_style` and all current profile fields backward compatible. Do not remove or rename the legacy fields.

Add a helper such as:

```python

def caption_defaults(profile: ChannelProfile | None, lang: str) -> CaptionStyle:
    """Build a valid CaptionStyle from this profile, selecting installed fonts safely."""
```

Implementation requirements:

1. Return the unchanged global `CaptionStyle()` for `profile is None`.
2. Start from `CaptionStyle()` and overlay only allowed `CaptionStyle` fields from `profile.caption_defaults`.
3. Pick the first installed font from `caption_font_preferences` and `headline_font_preferences` using `styles.available_fonts(lang)`.
4. For Khmer, prefer the language's native installed font/system fallback if the requested Latin font cannot render Khmer correctly.
5. Validate the result with `CaptionStyle.clean(lang)`.
6. Never allow unknown profile JSON keys to crash project creation.

The profile API endpoint already returns `p.model_dump()`, so the added profile fields should be exposed automatically. Update the TypeScript interface to match.

---

## 4. Caption and headline style changes

### `crcontent/styles.py`

Extend `CaptionStyle` while preserving old serialized drafts:

- Add `headline_font: str = ""` (`""` means use the caption font).
- Add `headline_color: str = "#FFFFFF"`.
- Add `headline_background: str = "#101419"`.
- Clean/validate the two new color fields with the existing `_hex()` helper.
- Validate `headline_font` against `available_fonts(lang)` just like `font`.
- Missing fields in existing `draft.json` should get defaults automatically.

Do not change the existing semantics of:

- `color`: non-spoken caption words
- `highlight`: currently spoken word
- `keyword`: script-marked keyword words

### `crcontent/captions.py`

Make the final ASS render use the exact same style as the preview:

1. Caption line uses `style.font` and its current three caption colors.
2. Headline line uses `style.headline_font or style.font or profile.font_name`.
3. Regular scene headlines use `style.headline_color` and a semi-opaque `style.headline_background`.
4. The opening hook card uses `style.highlight` as its accent fill and a readable dark foreground (`#101419`) for the text. If implementing adaptive contrast, calculate it from luminance and test it.
5. Preserve current hook sizing, line balancing, safe margins and timing.
6. Do not hard-code `#FFFFFF` / black headline treatment in a way that overrides the selected profile theme.

Use `ass_color()` for conversions. Remember ASS colors use a different channel order and alpha convention from CSS hex colors. Keep headline background alpha high enough to be readable but not fully opaque unless the style explicitly requests it.

### `frontend/lib/api.ts`

Extend `CaptionStyle` with the new headline fields and update `DEFAULT_CAPTIONS` with backward-compatible General values. Extend `ChannelProfile` with the caption defaults/font preference fields.

### `frontend/components/LivePreview.tsx`

Make the preview visually match the final FFmpeg/ASS render:

- Caption font comes from `style.font`.
- Headline font comes from `style.headline_font || style.font || language fallback`.
- Normal headlines use `headline_color` and `headline_background`.
- Opening hook uses `highlight` as its card accent and a contrasting dark text color.
- Keep the current draggable headline/caption positioning.
- Do not let a CSS class like `bg-white`, `text-[#141414]` or `bg-black/90` override the profile-controlled colors.

Add the following to `CaptionPanel`:

- Headline font selector
- Headline text color picker
- Headline background color picker
- Keep existing font, size, outline, word count, case and three caption color controls
- Add a small visual preview/swatches for normal, spoken, keyword and headline roles

A preset button should update the relevant preset fields without unexpectedly erasing the user's chosen headline font unless the preset explicitly provides one.

---

## 5. Apply the profile theme when a new project is created

### `crcontent/web.py` — `/api/script-video`

In the Short creation path, after `import_script(...)` and before `drafts.create(...)`:

- Resolve the already selected `profile`.
- If the profile is not `None`, set `script.captions` from the profile's caption defaults helper.
- If profile is `None`, leave `script.captions` untouched.
- Keep the selected profile ID/version on the Director Plan as it currently does.

This should apply to new projects only. Do not rewrite saved drafts or update existing videos when the profile registry changes.

For long videos, inspect the separate long-form rendering configuration before adding equivalent typography/grade defaults. Do not pretend the Short CaptionStyle automatically styles the independent long-form renderer. Implement the short path first, then add long-form support only if it can be done without duplicating style logic.

### Editor re-application

Add an explicit **Apply channel style** action in the Caption panel or project style controls. It should fetch/use the active project's channel profile and apply its defaults to the current project. Require a deliberate click so the user does not lose custom settings.

Do not add a new top-level editing mode. Channel profile remains the source of theme defaults; the existing editor remains shared.

---

## 6. Extend the visual system beyond captions

Implement these as profile-driven defaults in the shared editor/render pipeline. Do not fork the renderer per channel.

### Brand typography

- Caption font and headline font are independently configurable.
- Headline weight, case, letter spacing and size scale should be theme-aware.
- Keep text safe zones for YouTube Shorts UI overlays.
- Retain language-aware font fallback, especially for Khmer.

### Scene headlines and lower thirds

- Wildlife: high-contrast white headline, dark navy backing, yellow/gold action accent.
- History: parchment/ivory headline, charcoal backing, antique-gold accent; dates/places can use muted teal.
- Add a profile-aware lower-third style for person/place/date labels, with the same typography and palette.
- Do not add emoji to documentary headlines automatically.

### Motion graphics

Use profile defaults, but allow the creator to override them:

- Wildlife: slightly faster pop/scale, clean directional wipes, action-synced emphasis.
- History: slower reveal, map pans, document/photograph reveals, subtle line draws and restrained transitions.
- Avoid applying a motion effect to every scene. Motion must support the story beat, not decorate empty time.

### Color grading

- Wildlife: natural/vibrant grade with skin/feather/animal-color preservation.
- History: cinematic/film/mono options; do not recolor authentic archive footage so strongly that evidence details are changed.
- Store the grade choice in project state so preview and render agree.

### Sound design

- Wildlife: natural ambience and small action accents.
- History: restrained ambience, paper/map/mechanical details, rare impacts.
- Keep voice intelligibility primary and music/SFX ducking consistent.
- Respect the existing user music and licence workflow.

### Source and reconstruction labels

- Archive and evidence assets retain their provenance and source credit.
- AI reconstructions retain the existing visible `AI RECONSTRUCTION` label.
- Do not style stock/context footage as if it were the real historical event.

---

## 7. Profile picker preview

### `frontend/components/ScriptVideoForm.tsx`

When a user selects a profile, show a compact brand preview below the selector:

- Palette swatches
- Caption font and headline font preferences (or selected installed font)
- Three sample caption roles: normal / spoken / keyword
- Sample scene headline treatment
- One short description of its motion and sound direction

The selected profile should set the visual style, target duration, format and caption defaults for the new project. Keep the existing ability to manually change format, duration and other fields.

Do not force a style preset onto General projects.

---

## 8. Tests

Add or extend tests for the following.

### Profile defaults

- Both registered profiles round-trip through `ChannelProfile` validation.
- Wildlife profile returns its yellow/cyan/white caption palette and expected font preferences.
- Hidden History Files returns parchment/gold/teal caption colors and expected font preferences.
- Unknown profile still falls back to General as it does today.
- Profile with an unavailable preferred font falls back safely.
- Khmer profile does not force an unavailable or unsuitable Latin font.

### Backward compatibility

- Old `CaptionStyle` JSON without headline fields still loads.
- Legacy drafts with no channel profile preserve the current caption defaults.
- Existing channel profile persistence tests continue to pass.

### Render and preview parity

- `captions.caption_styles()` contains the configured headline font, text color and background color.
- Opening hook ASS uses the configured accent fill.
- Caption ASS still highlights the currently spoken word with `highlight` and marked words with `keyword`.
- Live preview uses the same field values and does not hard-code the old white/black headline colors.

### Project creation

- `/api/script-video` with `channel_profile_id="hidden_history_files"` creates a draft whose `script.captions` has the history defaults.
- `/api/script-video` with `channel_profile_id="wildlife_facts"` creates a draft with wildlife defaults.
- A project with no profile retains the old General defaults.
- Existing drafts are not rewritten by profile changes.

Run the focused pytest modules and frontend type/lint/build checks. Report any checks that cannot be run in the local environment.

---

## 9. Acceptance criteria

The work is complete when:

1. Selecting Wildlife Facts creates a project with its own caption and headline fonts, colors and visual defaults.
2. Selecting Hidden History Files creates a project with its own caption and headline fonts, colors and visual defaults.
3. Preview and final render show the same typography and colors.
4. The user can override every visual default in the existing editor.
5. The user can deliberately re-apply the selected profile style without changing narration, footage, timing or script content.
6. General projects and old drafts look exactly as they did before this change.
7. The system is data-driven: adding a third channel theme is primarily a new profile configuration, not a collection of new renderer conditionals.
8. No emojis are inserted into historical scene headlines by default.
9. History source attribution and reconstruction labels remain intact.

## Suggested implementation order

1. Extend `CaptionStyle` and ASS rendering (including hook and regular headline styles).
2. Add profile caption/font defaults and apply them to new Short projects.
3. Update TypeScript types, LivePreview and CaptionPanel controls.
4. Add profile picker style preview and explicit **Apply channel style** action.
5. Add profile-driven color-grade, motion-graphics, lower-third and sound defaults.
6. Add tests, run them, and update README documentation.

Keep the changes backward-compatible and make small, reviewable commits.
