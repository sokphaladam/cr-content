# Hidden History Files — Shorts Channel Implementation Specification

**Repository:** sokphaladam/cr-content  
**Target:** Add a history-documentary channel profile and production workflow without regressing the existing wildlife channel.  
**Format:** YouTube Shorts, vertical 9:16; default target 30–50 seconds (editable, aim for ~40 seconds).  
**Visual identity:** Cinematic historical documentary — midnight charcoal, antique gold, parchment and restrained teal.  
**Channel:** Hidden History Files

---

## 1. Executive decision

Do not build a second video editor and do not convert the current wildlife Shorts pipeline in place.

Build **Hidden History Files as a channel profile on the existing general Script-to-Video / AI Director workflow**. Reuse the current project model, timeline, footage planner, shot matching, editor, voiceover, captions, motion graphics, Remotion rendering, FFmpeg renderer, library and quality-inspection infrastructure.

The current dedicated Shorts Mode is animal-specific. It assumes an animal, animal-keyword searches, an animal-in-motion opening shot and an animal-facts hook judge. It must remain intact for the wildlife channel. History projects must not pass through those animal-specific rules.

The general Script-to-Video path is the preferred base because the repository already supports short-form projects, cinematic documentary styling, shot-level AI direction, evidence requirements, archival footage categories and a general footage matcher.

**Core product principle: One production engine, multiple channel profiles, separate editorial rules.**

A profile controls story rules, footage priorities, visual identity, captions, sound direction, preflight checks and metadata defaults. It must not fork the editor or renderer.

---

## 2. Verified current repository capabilities

Reuse these existing areas rather than reimplementing them:

| Existing area | Current role | History use |
|---|---|---|
| `frontend/components/ScriptVideoForm.tsx` | Paste a script, choose Short/Long, visual style, voice and music | Main history creation entry |
| `frontend/components/DirectorPlanPanel.tsx` | Review/edit AI shot plan; search and pick footage | History shot planning |
| `crcontent/ai_director.py` | Story phases, key facts, open loops, shot plans, factual requirements and sound design | Add history-specific direction |
| `crcontent/director_plan.py` | Shared Director Plan and shot/footage models | Add profile-aware metadata carefully |
| `crcontent/shot_footage.py` | Search candidates, judge visual relevance, retain source/license metadata | General history visuals |
| `crcontent/longform/footage.py` | General topic footage planning and providers | Reuse archival category and provider routing |
| `crcontent/longform/archives.py` | Internet Archive, NASA and The Met integrations | Historical archive sources |
| `crcontent/commons.py` | Wikimedia Commons search | Historical images and artifacts |
| `crcontent/plan_render.py` | Put Director Plan shots into existing renderers | Reuse for history |
| `crcontent/shorts/render.py` and general Short renderer | Portrait output, timeline, captions, audio, loop support | Reuse rendering, not animal validation |
| `crcontent/shorts/graphics.py` | ASS motion graphics | Reuse generic graphics where appropriate |
| `crcontent/shorts/motion.py` | Remotion fact popups and current map zoom | Extend map visuals |
| `crcontent/quality.py` and `crcontent/quality_preview.py` | Existing video quality inspection infrastructure | Add history-specific checks |
| `frontend/components/QualityInspector.tsx` | Quality inspection UI | Display history checks |
| `frontend/components/Timeline.tsx` and `frontend/components/LivePreview.tsx` | Timeline and preview | Keep shared |

### Important existing limitation

The dedicated `crcontent/shorts/` flow is wildlife-oriented:

- `shorts/directed.py` seeds the Director with `cinematic_wildlife`.
- `shorts/queries.py` requires animal search words.
- `shorts/hook.py` measures animal motion in the opening footage.
- `shorts/match.py` expects the right animal and checks animal-specific motion.
- `shorts/judge.py` evaluates hooks for an animal-facts channel.
- `shorts/preflight.py` enforces animal hook and loop requirements.

Do not weaken or remove these checks globally. History gets its own profile-specific checks on the general Script-to-Video path.

---

## 3. Product goals and non-goals

### Goals

1. Create and edit a Hidden History Files Short from a topic or finished script.
2. Produce source-backed historical scripts, with each key factual claim connected to evidence.
3. Plan shots as a cinematic documentary director: establishing view, artifacts, maps, archival records, details, reconstructions and payoff.
4. Search archival sources and general stock media with history-appropriate queries.
5. Make historical map sequences and evidence graphics.
6. Clearly distinguish authentic archival material, modern photographs, stock footage and AI-generated reconstructions.
7. Keep asset attribution and license details attached to the project and final post metadata.
8. Inspect history videos for factual and visual mismatches before render approval.
9. Preserve the existing wildlife workflow and all existing drafts, jobs, settings and output files.

### Non-goals for the first release

- A separate editor or renderer.
- Fully autonomous publishing to YouTube.
- Automatic generation of historically accurate changing borders without source geometry.
- Treating an LLM answer as proof of a historical claim.
- Assuming all Internet Archive or Wikimedia items are public domain.
- A mandatory paid image/video generation service.
- A long-form history documentary workflow in the first milestone.
- A new analytics system; existing analytics can be reused later.

---

## 4. Channel profile architecture

### 4.1 Profile selection

Add a channel/profile selector to the general Script-to-Video creation flow. The first two profiles are:

**Wildlife Facts**
- Maps to the existing wildlife behavior and visual defaults.
- Existing behavior remains the default for existing users and saved projects.
- Do not silently convert existing drafts.

**Hidden History Files**
- Profile ID: `hidden_history_files`
- Format: Short
- Visual style: `cinematic_history` (new profile-aware style; do not replace `cinematic_documentary`)
- Palette: midnight charcoal, antique gold, parchment and restrained teal
- Voice direction: measured, curious, authoritative; not horror-trailer delivery
- Story model: hook → historical context → clues/evidence → revelation → consequence or thoughtful final question
- Visual priority: authentic primary/archival material where available, then reputable museum/heritage images, then fitting stock context, then clearly labelled reconstructions.

### 4.2 Profile configuration

Introduce a validated profile model and a profile registry. Exact storage path can follow existing settings conventions, but profile configuration must be separate from per-project state.

Recommended profile fields:
- `id`, `display_name`, `version`
- `format_defaults`: aspect ratio, target duration, frame rate
- `visual_style`, `palette`, `caption_style`, `font_preferences`
- `voice_defaults`, `music_mood`, `sound_design_defaults`
- `story_rules`: structure, hook deadline, pacing, ending rules
- `research_rules`: required source evidence and corroboration policy
- `footage_priority`: archive, museum, Wikimedia, licensed stock, user media, reconstruction
- `preflight_rules`: enabled checks and severity
- `metadata_defaults`: description format, source-credit format and pinned-comment template

Use a versioned schema. Unknown profile IDs must safely fall back to existing default behavior and show a non-fatal warning.

### 4.3 Persist profile identity

Persist `channel_profile_id` and `channel_profile_version` in:
- new draft metadata;
- Director Plan/project metadata;
- job `meta.json`;
- exported project metadata;
- rendered output metadata.

Existing drafts with no profile ID must be treated as the current default; do not migrate them to the history profile.

### 4.4 Profile UI

In the Script-to-Video creation form:
- Add a compact Channel profile selector before script/topic input.
- Show profile name, short description and visual preview.
- Use the selected profile to set defaults, but allow per-project overrides.
- Persist the selection for the next project.
- Display the active profile in the editor header, Director panel and preflight report.
- Do not add a new top-level editor mode unless necessary. The profile configures the existing workflow.

---

## 5. History research and fact verification

This is the most important new capability. A history Short must not be generated from model memory alone.

### 5.1 Research-first workflow

Provide two entry paths.

**Topic workflow**
1. User enters a topic, question or mystery.
2. Research planner creates a research brief.
3. App gathers sources and extracts candidate claims.
4. App identifies contradictions, uncertainty and missing evidence.
5. User reviews/approves the brief.
6. Scriptwriter creates a Short from approved claims.
7. AI Director plans visuals from the approved script and evidence.

**Finished-script workflow**
1. User pastes a script.
2. Claim extractor breaks it into atomic factual claims.
3. Researcher attaches evidence or flags unsupported statements.
4. User resolves warnings.
5. AI Director and production proceed.

Do not force every existing Script-to-Video user into research-first mode. It is a profile-specific workflow.

### 5.2 Data model

Create a small history domain package, suggested location `crcontent/history/`.

**ResearchBrief**
- `id`, `topic`, `created_at`, `updated_at`
- `period`, `places`, `people`, `entities`
- `summary`
- `timeline_events[]`
- `claims[]`
- `sources[]`
- `contradictions[]`
- `open_questions[]`
- `research_status`: `draft | needs_review | approved`

**HistoricalClaim**
- `id`
- `claim_text`
- `claim_type`: date, person, location, event, cause, consequence, quantity, interpretation
- `status`: `supported | disputed | uncertain | unsupported`
- `importance`: `central | supporting | optional`
- `source_ids[]`
- `notes`
- `script_scene_ids[]`

**ResearchSource**
- `id`, `title`, `publisher`, `author`
- `url`, `source_type`
- `publication_date`, `accessed_at`
- `relevant_excerpt` or a concise evidence note
- `source_role`: primary, scholarly_secondary, museum_or_archive, reference
- `license_note` only when the source also provides a visual asset
- `content_hash` or cache key when practical

Do not use an LLM-generated numeric “truth score” as a substitute for source evaluation.

### 5.3 Evidence rules

- Central claims require at least one directly relevant, credible source; prefer corroboration by an independent source.
- Important dates, casualty counts, quotations, named individuals and causal claims must be explicitly supported.
- Primary sources are valuable but must be contextualized; a primary source can be biased or incomplete.
- Prefer universities, peer-reviewed research, archaeological projects, museums, national archives, heritage organizations and reputable reference institutions.
- Wikipedia can help discover terminology and references, but should not be the sole evidence for a central claim.
- Separate what is known from what is debated.
- If sources disagree, record the disagreement and use careful wording in the script.
- Do not turn “no surviving evidence” into “nobody knows”.
- Do not call an event “unsolved” when credible evidence has resolved it.
- Do not invent dates, quotations, locations, eyewitness accounts or expert consensus.
- The app must show source links beside the claims they support.

### 5.4 Source discovery architecture

Use a provider interface so sources can be added without coupling research logic to one API.

Required initial capabilities:
- User-added source URLs and notes.
- Search-result import from a configured/available research provider.
- Existing archival and museum provider metadata reused for visual discovery.
- Optional cached page text or user-supplied excerpts, subject to access and provider rules.

Do not assume Gemini's general knowledge provides citations. An LLM can propose search queries, summarize supplied material and map claims to source excerpts, but it cannot mark a claim supported unless evidence is attached.

Provider failures should leave the brief editable and show which sources could not be retrieved. Never fabricate an empty or inaccessible source.

### 5.5 Research UI

Add a Research panel or step with:
- topic and historical period;
- source list with publisher, title, URL and source type;
- claim list with status and linked source chips;
- supported / disputed / uncertain / unsupported states;
- contradictions and unanswered questions;
- actions to add a source, edit a claim, re-check claims and approve brief;
- a clear “not yet researched” state.

The user must be able to edit research manually and continue when a search provider is unavailable.

---

## 6. History storytelling and AI Director

### 6.1 Add a history visual style

Extend `director_plan.STYLES` and the frontend visual-style types with `cinematic_history`. Keep all current style IDs backward compatible.

The history style should be selected by the History profile and passed through the existing Director Plan. Do not hard-code history instructions into all documentary projects.

### 6.2 History AI Director behavior

Add profile-specific prompt instructions to the existing AI Director.

The Director should:
- preserve approved narration word-for-word unless the user explicitly asks for a rewrite;
- build a clear question in the first 1–2 seconds;
- choose a single central historical mystery or discovery;
- establish time and place quickly;
- reveal clues in a meaningful order;
- distinguish evidence from dramatization;
- end with a satisfying revelation, consequence or carefully framed unresolved question;
- avoid artificial danger, exaggerated claims and conspiracy framing;
- avoid using generic “ancient temple” footage to imply a specific event occurred there;
- use close-up artifact details, inscriptions, documents, maps, landscapes, excavation imagery and archival footage as evidence shots;
- include 1–5 purposeful shots per narration scene, depending on timing;
- keep shots readable on a phone;
- plan sound design in support of the story, not as constant noise.

### 6.3 History narrative structure

Default 30–50 second structure:

1. **Hook (0–3s):** surprising evidence, consequence or specific question; no channel intro.
2. **Context (3–10s):** who, where and when.
3. **Investigation (10–25s):** clues, records, artifacts or conflicting explanations.
4. **Revelation (25–40s):** what the evidence actually shows.
5. **Resonance (final seconds):** why it matters or what remains uncertain.

Durations are guidance, not rigid scene boundaries. The user can change target length.

The loop is optional. Do not force a mid-sentence ending if it makes a historical conclusion confusing. When used, it must be natural and must not misrepresent the evidence.

### 6.4 History hook judge

Create a profile-aware hook evaluation. It should judge:
- specific curiosity;
- concrete historical subject;
- clarity in the first 1–2 seconds;
- truthful wording;
- alignment with the first visual;
- promise/payoff consistency.

Do not use the animal-specific hook judge for history.

---

## 7. Historical footage, asset discovery and rights

### 7.1 Reuse the existing general footage pipeline

Prefer the existing general Script-to-Video `longform/footage.py` and `shot_footage.py` pathways for history. They already distinguish archival, footage, graphic and montage, and the archival category includes history-oriented sources.

Verify that general Short projects use the history-capable path in portrait mode. Do not route history through `shorts/footage.py` or `shorts/queries.py` unless those modules have first been made profile-aware and all wildlife constraints have been removed from the history branch.

### 7.2 History source priorities

Default order, subject to actual search quality and the asset's rights:

1. User-supplied files and selected source material.
2. Exact historical archive footage or photograph.
3. Museum, library, university or archaeological project imagery.
4. Wikimedia Commons asset with an individually verified license.
5. Licensed general stock for atmosphere or context.
6. Clearly labelled AI reconstruction when authentic visuals do not exist.

A source category alone does not prove rights. Validate the individual asset's page, author and license. In particular, do not assume every Internet Archive upload is public domain merely because it is hosted on the Archive.

### 7.3 Asset provenance

Every selected asset should retain:
- provider/source name;
- source page URL;
- asset title or ID;
- author/creator where available;
- license label and license URL;
- download/access date;
- asset type: archival, current photograph, stock, map, graphic or AI reconstruction;
- whether the asset depicts the actual event or is illustrative.

If the source has no reliable license information, mark it `rights_unknown` and require user review. Do not silently treat it as cleared.

### 7.4 Match footage to historical claims

Extend shot validation language to judge:
- correct person, artifact, building, location or event;
- correct period and visual context;
- whether the asset actually shows the narrated action/event;
- whether the footage is authentic, illustrative or reconstructed;
- whether the visual could mislead the viewer about the time or place.

Do not use a generic visual match as proof that a specific historical event happened.

### 7.5 Credits

Generate a source-credit section in the video's `post.txt`/description metadata using retained provenance. Do not drop author, source or license fields when shots are rearranged or replaced. Avoid duplicate credit lines.

---

## 8. Historical map animation

The current Remotion map zoom is a useful starting point, but it locates a modern place named in the voiceover. It does not prove historical borders or territorial extent.

### 8.1 MVP

Extend the existing Remotion map rendering with a history-map mode that supports:
- location marker and label;
- period/date label;
- route line with directional movement;
- multiple locations;
- zoom from regional to local context;
- highlighted area only when a user/source supplies the geometry;
- map attribution/source note.

### 8.2 Data model

Suggested HistoricalMapSequence:
- `id`, `title`, `period_label`
- `base_map_source`, `base_map_attribution`
- `markers[]`: label, latitude, longitude, event date, note
- `routes[]`: ordered coordinate points, label, direction, event date
- `regions[]`: polygon/GeoJSON reference, source URL, date range, confidence/status
- `keyframes[]`: time, zoom, center, visible layers
- `source_ids[]`

Do not have AI invent a historical border polygon. If no trustworthy geometry exists, show a location marker, route or sourced historical map image instead.

### 8.3 Editor controls

In the Director/shot editor, allow:
- map shot type;
- selected period;
- map source;
- markers and routes;
- date labels;
- animation duration;
- preview and manual correction.

A map shot must be optional and editable like any other shot.

---

## 9. Historical scene reconstruction

AI reconstruction is valuable for lost cities, ancient markets, ships, clothing and daily life. It is also a major source of accidental misinformation.

### Requirements

- Reuse the current image-generation/art system where suitable; keep provider integration behind an adapter.
- Require approved research facts and period notes as the reconstruction brief.
- Keep known architecture, clothing, tools and environment consistent with the evidence.
- Do not depict a disputed detail as certain.
- Never describe generated imagery as authentic archival footage.
- Store `visual_origin = ai_reconstruction` in project metadata.
- Add an unobtrusive label such as “AI reconstruction” where needed to prevent viewer confusion.
- Let users regenerate, replace, crop, animate or reject the asset.
- Do not make a paid generation API mandatory for the first release.

Reconstruction prompt data should include:
- period and location;
- verified visual details;
- details that must not be invented;
- camera/framing notes;
- aspect ratio;
- whether the image is illustrative or a proposed reconstruction.

---

## 10. Visual identity and editing preset

Add a Hidden History Files preset that configures, but does not lock, editor controls.

### Brand system

| Element | Default |
|---|---|
| Primary background | Midnight charcoal `#101419` |
| Accent | Antique gold `#B99A60` |
| Text | Parchment `#D6C9AC` |
| Secondary accent | Mystery teal `#315C60` |
| Main title font | Bebas Neue or Anton (if available) |
| Supporting font | Inter or Montserrat (if available) |
| Editorial serif | Cormorant Garamond (if available) |
| Caption emphasis | Antique gold |
| Narration emphasis | Warm white/parchment |

Use fonts that are legally distributable with the app. Provide safe fallbacks when a font is missing.

### Editing direction

- 1080×1920, 30fps output.
- Documentary-grade contrast and readable shadows.
- Restrained gold labels for dates, locations and names.
- Evidence overlays: source dates, artifact IDs, map pins and short document excerpts.
- Slow push-ins on stills; deliberate camera movement on footage.
- Map transitions and match cuts where meaningful.
- Subtle film grain and vignette only when they improve legibility.
- Low, restrained ambience; use impacts only for real story beats.
- No constant glitch effects, fake film burns or generic horror stingers.
- Captions must stay within safe zones and not cover artifacts, faces, maps or key evidence.

Preset must be editable and must not alter wildlife or lyric-video presets.

---

## 11. History-specific preflight and quality inspection

Build on the existing preflight/Quality Inspector rather than creating a separate QA application.

### 11.1 Checks

**Research and factual accuracy**
- Every central factual claim maps to at least one attached source.
- Unsupported claims are visibly flagged.
- Disputed claims use qualified language.
- Dates, names, numbers and quotes match attached evidence.
- The ending does not imply a mystery is unresolved if research says otherwise.

**Visual accuracy**
- Visual period is not obviously inconsistent with narration.
- An illustrative image is not presented as actual event footage.
- AI reconstructions are identified in metadata and, where needed, on screen.
- Map markers, routes and borders have source data.
- Footage matches the planned subject and action.
- No accidental unrelated, modern or misleading stock clip.

**Rights and attribution**
- Every externally sourced asset has provenance.
- Rights-unknown assets are flagged.
- Credits contain available creator/source/license data.
- No unsupported blanket public-domain assumption.

**Video quality**
- 9:16 dimensions, frame rate and audio checks.
- Caption safe-zone and readability.
- No black frames, broken media, accidental empty scenes or audio gaps.
- Voice/music balance and clipping.
- Smooth scene boundaries and motion.
- Export duration matches the approved script.

### 11.2 Status model

Use three explicit states:
- `ready`: all mandatory checks passed.
- `review_required`: warnings or uncertain rights/claims need creator review.
- `blocked`: missing central source evidence, broken media, invalid render or a severe misleading visual/claim.

Never mark a video ready solely because an LLM gives it a high score.

Creator approval is required before rendering when the report contains unresolved review items. Keep a deliberate override with an audit note for non-critical warnings; never allow it to conceal source or rights uncertainty.

---

## 12. UI workflow

The intended creator experience:

1. Select Hidden History Files profile.
2. Enter a topic or paste a finished script.
3. Open Research Brief and review claims/sources.
4. Approve claims or revise unsupported wording.
5. Generate the history script and choose voice/target duration.
6. Open AI Director and inspect the story arc and shots.
7. Search/swap archival footage, museum imagery, stock context and reconstructions.
8. Configure optional map or evidence graphics.
9. Edit captions, dates, sound, transitions and timing in the shared editor.
10. Run History Preflight / Video Quality Inspector.
11. Review credits and disclosure labels.
12. Approve and render.
13. Export video, thumbnail/cover if enabled, description, source credits and production metadata.

Keep the normal editor and preview interactions. Do not introduce a second timeline.

---

## 13. Implementation milestones

Each milestone should be independently testable and should preserve current production behavior.

### H1 — Channel Profile Foundation

**Scope**
- Add profile registry and versioned schema.
- Add Wildlife Facts and Hidden History Files profiles.
- Add profile selector to general Script-to-Video.
- Persist profile ID/version in drafts, plans, jobs and output metadata.
- Add profile-aware style and editor defaults.
- Make profile selection visible in editor and preflight.

**Likely files**
- `crcontent/director_plan.py`
- `crcontent/config.py` or a dedicated profile/settings module
- `crcontent/ai_director.py`
- `frontend/lib/api.ts`
- `frontend/components/ScriptVideoForm.tsx`
- `frontend/app/page.tsx`
- relevant settings/API handlers in `crcontent/web.py`

**Acceptance criteria**
- User can select Hidden History Files and create a Short.
- New project metadata records the profile.
- Existing drafts and wildlife defaults behave exactly as before.
- No change to dedicated wildlife Shorts Mode rules.
- Profile unknown/missing fallback is safe and visible.
- Unit tests cover profile loading, validation, versioning and legacy defaults.

### H2 — Research and Claim Verification

**Scope**
- Add `crcontent/history/` domain package.
- Add research brief, source and claim models.
- Add source URL/manual source support.
- Add source discovery provider interface.
- Add claim extraction and claim-to-source mapping.
- Add Research UI with statuses and approval.
- Persist research brief beside its project.

**Likely files**
- new `crcontent/history/models.py`
- new `crcontent/history/research.py`
- new `crcontent/history/sources.py`
- new `crcontent/history/claims.py`
- relevant endpoints in `crcontent/web.py`
- new frontend Research panel and API types/client calls

**Acceptance criteria**
- Topic produces a research brief with source links or explicitly reports that discovery is unavailable.
- A pasted script can be split into atomic claims.
- Every central claim shows its supporting source(s) or an explicit unsupported status.
- Contradictory sources remain visible.
- LLM memory alone cannot mark a claim supported.
- Approved brief is versioned and associated with the project.
- Tests cover missing sources, duplicates, conflicting evidence, inaccessible URLs and model hallucination-shaped output.

### H3 — History Storytelling and AI Director

**Scope**
- Add cinematic_history visual style.
- Add profile-specific history Director instructions.
- Add history script prompt/template using the five-stage story model.
- Add history hook judge.
- Pass approved key facts and claim IDs into the Director Plan.
- Add a fact/evidence view in DirectorPlanPanel.

**Likely files**
- `crcontent/ai_director.py`
- `crcontent/director_plan.py`
- `crcontent/shot_footage.py`
- `frontend/components/DirectorPlanPanel.tsx`
- `frontend/components/ScriptVideoForm.tsx`
- `frontend/lib/api.ts`

**Acceptance criteria**
- History profile prompts for evidence-first visuals, not animal footage.
- First 1–2 seconds establish a clear specific curiosity gap.
- Director distinguishes archive, context, evidence, graphic and reconstruction shots.
- The same script under Wildlife Facts still receives wildlife behavior.
- Narration changes only when explicitly requested.
- Tests cover style routing, history hook scoring and backward-compatible plan deserialization.

### H4 — Archival Shorts Footage Integration

**Scope**
- Ensure general Short project footage uses the archival-capable general provider pipeline.
- Use history search queries that include entity, location, period and event.
- Preserve source, author, license and source page through candidate selection, editing and export.
- Extend visual matching for person/artifact/building/event/period/action.
- Add asset origin and rights status to storyboard/preflight.

**Likely files**
- `crcontent/longform/footage.py`
- `crcontent/longform/archives.py`
- `crcontent/shot_footage.py`
- `crcontent/director_plan.py`
- `crcontent/plan_render.py`
- `crcontent/longform/storyboard.py`
- relevant API/UI components

**Acceptance criteria**
- A History Short can find an archive image or clip when a suitable one exists.
- A failed archival search falls back to another source without pretending the fallback is authentic.
- Search result and selected asset both retain source page and rights metadata.
- Rights-unknown assets are flagged for review.
- Visual matching can reject a wrong period/person/artifact.
- Wildlife search and animal match tests remain unchanged and pass.

### H5 — Historical Map Animator

**Scope**
- Extend Remotion map rendering with history overlays.
- Add markers, routes, period labels, map zoom and sourced region shapes.
- Add a map sequence model and editor panel.
- Allow source geometry or user-provided GeoJSON for historic boundaries.
- Store source attribution and date range per layer.

**Likely files**
- `crcontent/shorts/motion.py` or a shared map renderer
- `remotion/src/MapZoom.tsx` and new history map components
- `crcontent/director_plan.py` or a dedicated history map model
- `frontend/components/DirectorPlanPanel.tsx`
- `frontend/lib/api.ts`

**Acceptance criteria**
- A Short can render a sourced point marker and route.
- A sequence can show a dated map state.
- Region/border overlays require sourced geometry.
- Missing geometry produces an honest marker/route fallback.
- Map labels remain legible in 9:16 and respect caption safe zones.
- Existing map_zoom still works.

### H6 — Historical Reconstruction and Motion Graphics

**Scope**
- Add a reconstruction asset type and structured prompt builder.
- Use approved period facts and visual requirements.
- Add an AI reconstruction provenance label.
- Add evidence graphics: dates, timeline, artifact callouts, document excerpts and sourced comparisons.
- Reuse current image generation and Remotion infrastructure where possible.

**Likely files**
- existing image generation adapter/module
- `crcontent/ai_director.py`
- `crcontent/director_plan.py`
- `crcontent/shorts/graphics.py`
- Remotion components
- `frontend/components/SceneCard.tsx`
- `frontend/components/DirectorPlanPanel.tsx`

**Acceptance criteria**
- AI reconstruction is stored distinctly from archival material.
- Every reconstruction can be reviewed/replaced by the creator.
- The system does not invent precise unsupported architecture, costume or event details.
- The final video does not label AI imagery as genuine historical footage.
- No paid external image generator is mandatory.

### H7 — History Preflight and Quality Inspector

**Scope**
- Add history checks to existing QC.
- Add source/claim/shot traceability.
- Add rights and reconstruction warnings.
- Add final credit generation.
- Add the three-state status model and review UI.

**Likely files**
- `crcontent/quality.py`
- `crcontent/quality_preview.py`
- `crcontent/shorts/preflight.py` only where shared/general hooks are safe
- `frontend/components/QualityInspector.tsx`
- storyboard/preflight rendering and metadata export code

**Acceptance criteria**
- Report points from each factual claim to its source.
- Report identifies unsupported/disputed claims.
- Report distinguishes archival, modern stock and AI reconstruction.
- Rights-unknown assets are never silently cleared.
- Broken/low-quality visual and audio checks work.
- A video cannot be ready when a central claim lacks evidence or a severe visual mismatch remains.
- Existing wildlife and lyric QC tests remain green.

---

## 14. Testing strategy

### Unit tests
- profile schema validation and fallback;
- existing draft migration/default behavior;
- history claim extraction;
- claim/source association;
- duplicate source handling;
- source conflict representation;
- URL retrieval failure;
- history prompt/style selection;
- map coordinate and date validation;
- sourced geometry requirement;
- asset provenance and rights-state persistence;
- credit rendering and deduplication;
- AI reconstruction label persistence.

### Integration tests
- topic → research brief → approved claims → script → Director Plan;
- finished script → claim extraction → research review;
- history Short → archive search → storyboard → render;
- history Short with no archive results → contextual stock/graphic fallback;
- history map point/route → Remotion output;
- AI reconstruction → editor review → render metadata;
- QC report → approval gate.

### Regression tests
- wildlife Shorts spreadsheet workflow;
- wildlife animal hook motion test;
- wildlife footage query construction;
- current Script-to-Video Short and Long flows;
- existing AI Director project load/save;
- plan rendering and manual footage locks;
- lyric-video rendering and Animated Cover;
- existing Quality Inspector checks.

### Manual acceptance scenarios

**Scenario A: Mahendraparvata**
- Topic: “The lost city hidden beneath Cambodia's jungle”.
- Research brief separates prior knowledge of the site from what LiDAR revealed.
- Script avoids claiming LiDAR discovered the city for the first time.
- Visuals use Phnom Kulen landscape, archaeological plans, sourced imagery and labelled reconstruction.
- Map shows the sourced location; it does not invent the city's boundary.
- Final credits include every externally sourced visual.

**Scenario B: Voynich Manuscript**
- Script says the manuscript's script remains undeciphered, rather than inventing a definitive translation.
- Visuals distinguish actual manuscript pages from illustrative reenactments.
- Sources are attached to manuscript date, provenance and decipherment claims.

**Scenario C: Mary Celeste**
- Script distinguishes documented facts from popular legends.
- A generic ghost ship image is labelled illustrative, not actual footage.
- Ending does not claim that all explanations are impossible.

---

## 15. Data compatibility and migration rules

1. Do not rename or repurpose current wildlife settings keys.
2. Do not change `shorts.json` defaults for existing users.
3. Existing short jobs without a profile ID continue as wildlife/dedicated Shorts jobs according to their existing kind.
4. General Script-to-Video projects without a profile ID keep current general documentary defaults.
5. New history projects explicitly store `hidden_history_files`.
6. Add new Pydantic fields with safe defaults and maintain migration logic in `director_plan.py`.
7. Preserve old `plan.json`, `draft.json`, `meta.json` and cached footage loading.
8. Never rewrite existing output files or user-selected media during migration.

---

## 16. API and UI design constraints

- Follow existing API client and FastAPI route conventions in `crcontent/web.py` and `frontend/lib/api.ts`.
- Keep Python models as the source of truth and expose typed TypeScript counterparts.
- Use explicit project/profile IDs in requests; do not infer profile from a title string.
- Keep expensive research and footage discovery asynchronous using the existing job/progress pattern.
- Cache research retrieval and visual search with explicit invalidation when source content or claims change.
- Do not block the editor if one provider is unavailable.
- Keep all new external provider credentials optional and documented in Settings.
- Never expose API keys or private source content in `post.txt`.
- Keep profile-specific behavior in profile-aware services, not broad global prompt mutations.

---

## 17. Recommended delivery order

Implement and test in this order:

1. H1 — profile foundation and safe routing.
2. H2 — source-backed research.
3. H3 — history storytelling and Director.
4. H4 — archival integration into general Shorts.
5. H7 core checks — minimum historical claim/source/rights QC before real publishing.
6. H5 — map animation.
7. H6 — historical reconstructions and richer evidence graphics.
8. H7 completion — full QC, attribution and approval experience.

H7 has a milestone number for planning, but its minimum source/rights checks must arrive before the first public history upload. Do not postpone basic factual and rights verification until the end.

### Suggested first usable release

A first usable Hidden History Files release is achieved when H1–H4 are complete and the minimum H7 research/rights gates are in place. It must produce a source-backed Short using authentic archival/museum imagery and general context footage, with correct voiceover, captions, credits and manual creator approval.

---

## 18. Definition of done

The feature is done when:
- Hidden History Files is selectable as a profile.
- The existing wildlife channel still works as before.
- The app can research a historical topic and attach evidence to claims.
- The user can approve or correct research before script generation.
- The history AI Director produces history-appropriate shot plans.
- Archival and general footage can be searched and reviewed in portrait projects.
- Historical maps use sourced locations/routes/geometry.
- AI reconstructions are clearly distinguished from genuine archival assets.
- History-specific preflight catches unsupported claims, misleading visuals and rights uncertainty.
- Exported video and description carry accurate asset credits.
- All relevant automated tests pass.
- Manual tests of Mahendraparvata, Voynich and Mary Celeste complete without using animal-specific rules.
- No existing wildlife, lyric-video or general Script-to-Video workflow regresses.

---

## 19. Implementation instruction for the coding agent

Before coding each milestone:

1. Read the current implementation and tests for every affected path.
2. Trace the exact general Script-to-Video Short request path from ScriptVideoForm through `crcontent/web.py`, draft creation, AI Director, `shot_footage.py`, `plan_render.py` and the renderer.
3. Confirm which archival providers are actually enabled for general portrait Shorts; do not infer integration from module comments alone.
4. Implement the smallest end-to-end vertical slice.
5. Add unit, integration and regression tests in the same milestone.
6. Run the relevant test suite and report exact commands/results.
7. Update docs and settings examples.
8. Do not mark a milestone complete based only on UI controls or prompt text. Demonstrate that its output reaches the renderer and is present in the exported video/metadata.

**Do not implement all seven milestones as one large refactor.** Deliver H1 first, verify that wildlife behavior is unchanged, then proceed milestone by milestone.

---

## 20. Progress

- [x] **H1 — Channel Profile Foundation** (2026-11-07)
  - `crcontent/profiles.py`: versioned `ChannelProfile` schema (`SCHEMA = 1`) and registry with `wildlife_facts` and `hidden_history_files`. `resolve("")` means General (the pre-profile defaults). An unknown ID, or a profile made for a newer schema, falls back to General and returns a warning (`profile_note`); it never fails.
  - `director_plan.py`: new style `cinematic_history`; `Project.channel_profile_id` / `channel_profile_version` default to `""` / `0`, so old `draft.json`/`plan.json` files load unchanged.
  - `web.py`: `GET /api/profiles`; `POST /api/script-video` accepts `channel_profile_id` and tags the plan before the AI Director runs (Short draft, Long prose, Long table). Profile ID/version/name are written to the long video's `meta.json` and to the rendered draft video's `meta.json` (`profiles.stamp`).
  - `quality.py`: the render report carries `channel_profile`, which the Quality Inspector shows next to the check profile.
  - UI: a Channel profile selector at the top of Script to Video (General / Wildlife Facts / Hidden History Files) with a description and palette swatches. Picking a profile sets the style, target length and format, and each can still be changed. The choice is remembered in localStorage. The Director panel shows a "Channel" chip.
  - Not touched: the Shorts Mode (`crcontent/shorts/`) wildlife rules and `shorts.json`. Picking Wildlife Facts only sets defaults (style `cinematic_wildlife`); General keeps `cinematic_documentary`.
  - Tests: `tests/test_channel_profiles.py` (9). Full suite: `.venv/Scripts/python -m pytest -q` → 462 passed; `npx tsc --noEmit` and eslint are clean.
  - Follow-up (same day): the draft editor's title bar shows a profile badge, and the pre-render check (`quality_preview.inspect_short`) reports `channel_profile` too.
  - Browser check (scratch library, no API key): picking Hidden History Files set style `cinematic_history` and target 0:40, with 4 palette swatches. The choice survived a reload. The created draft saved `hidden_history_files` v1 with target 40. The editor header badge, the Director "Channel" chip and the pre-render header "Shorts profile · Hidden History Files" all showed. A General Short saved `channel_profile_id: ""` and `cinematic_documentary`.
  - Open: the AI Director prompt doesn't read the profile yet (H3).
- [x] **H2 — Research and Claim Verification** (2026-11-07)
  - `crcontent/history/`:
    - `models.py`: ResearchBrief, HistoricalClaim, ResearchSource, Evidence, Contradiction, TimelineEvent.
    - `sources.py`: two providers. Gemini with Google Search grounding reads Google's `groundingMetadata`, follows the redirect links to the real page, and keeps only pages the answer actually rests on. The Wikipedia API returns article intros (a topic is looked up as written; a script by the proper names it mentions). Also `add_url` for sources added by hand, duplicate merging by normalised URL, and a first guess at each source's role from its domain.
    - `claims.py`: splitting text into claims (Gemini, or one claim per checkable sentence without a key; topics are capped at 15 claims), matching claims to evidence, and `settle()`.
    - `research.py`: the run (3 job steps), saving, editing, approval.
  - The evidence rule (`claims.settle`, plain code):
    - evidence must point at a stored source and carry an excerpt;
    - backing + disputing → disputed;
    - backing only → supported, except a central claim backed by Wikipedia alone → uncertain;
    - nothing attached → unsupported;
    - the creator can mark a claim less sure than its evidence, never more.
    - Excerpt or claim ids the model invents are dropped. A page that couldn't be opened is kept, flagged with `retrieval_error`, and isn't evidence until the creator adds the passage.
  - Storage: `research.json` in the draft's or long video's folder; topic briefs in `<data>/research/<id>.json`. `revision` goes up on every save, `approved_revision` / `approved_at` record approval, and any later save sets the status back to needs_review. Approval is refused (409) while a central claim has no source. Every provider failure is written to `provider_notes`, and the brief stays editable.
  - API: `POST /api/research/topic`, `GET|PUT /api/research/{draft|long|topic}/{ref}`, `POST .../run` (a background job; a second click returns the same job), `POST .../sources`, `POST .../approve`.
  - UI: `ResearchPanel.tsx`. It shows the claims (status, importance, "mark as", evidence with source links, attach a passage, add/remove), disagreements and open questions, sources (role, provider, unreadable-page warning, add by link with note and passage), and Approve. It appears in a "Research" editor tab (Hidden History drafts only) and in "Research a topic first" in the create form (History profile only).
  - Tests: `tests/test_history_research.py` (18): missing sources, duplicates, conflicting evidence, unreachable URLs, invented ids and "supported" claims from the model, Wikipedia-only central claims, no-key runs, the API flow. Full suite: 480 passed; tsc and eslint clean.
  - Live check (scratch library, real Gemini key):
    - Scenario A script: 4 claims, all supported by angkordatabase.asia, Cambridge *Antiquity* and others; Wikipedia found Mahendraparvata, Phnom Kulen and Cambodia.
    - In the UI: marking a claim "uncertain" locked it; an unsourced central claim blocked approval; removing it allowed approval (r5).
    - Scenario C topic (Mary Celeste): 10 claims; a Wikipedia-only central claim was marked uncertain; rmg.co.uk was labelled museum/archive.
  - Open:
    - A grounded "excerpt" is the sentence Gemini wrote that Google tied to the page, not a quote copied from the page. The UI shows it as the passage; the creator should open the link for anything central.
    - The long-video storyboard page has no Research tab yet (the API supports `long`).
    - Topic briefs can't be listed or reopened after leaving the form (they are on disk). They are turned into a script in H3.
- [x] **H3 — History Storytelling and AI Director** (2026-11-07)
  - Routing: `ai_director.is_history(plan)` is true for the `hidden_history_files` profile or the `cinematic_history` style. History projects get:
    - extra instructions (`HISTORY`: the five-stage story model, evidence-first visuals, no animal footage, no hype or conspiracy framing, a loop only when natural);
    - a history Short format (30-50 s, a specific question in the first 1-2 s);
    - a shot schema that requires `visual_origin` (archive / evidence / context / graphic / reconstruction).
    - The wildlife channel's imported analytics (hook styles, animal subjects) are no longer sent for history.
    - Every other project gets exactly the old prompt and schema (tested).
  - Plan model (all default empty, so old plans load): `Shot.visual_origin`, `Scene.claim_ids`, `Story.research_revision`.
  - Research → plan: `ai_director.link_research` (plain code) puts an **approved** brief's claims into the plan: each scene's claim ids (from the claims' scene ids), central claims as `story.key_facts`, and the approved revision. It runs when you approve a draft's or long video's research, when you direct with AI (the Director also gets the sourced claims and their statuses in its prompt; unsupported claims are never offered), and when a Short is made from a topic script. A brief edited after approval (`needs_review`) links nothing.
  - Script from research: `history/script.py` and `POST /api/research/topic/{id}/script`.
    - Only an approved brief's sourced claims are used. Disputed and uncertain claims must be worded with qualifiers. The first line must open a question.
    - Invented claim ids are dropped. Missing ids are filled in from the claims whose key words and numbers the scene repeats (≥40%).
    - A flat opening or an unsourced claim comes back as a warning.
    - The text goes into the form for review; nothing is created until "Create video". `script-video` with `research_brief_id` copies the approved topic brief into the new draft (`research.json`) and links its claims to the plan's scenes by narration text.
  - History hook judge: `history/hook.py`, plain rules. It checks: no intro, a concrete subject, a curiosity gap, clarity in the first ~6 words, truthful wording (hype words; a disputed or uncertain claim without qualifiers fails), the first shot matching the hook (and not a reconstruction), and a payoff. It runs in the pre-render check as `history.hook.*`, for history plans only. The wildlife judge (`shorts/judge.py`) is never used here.
  - UI:
    - Director panel: visual-origin labels on shots, each scene's claims with status and source links, a warning while research isn't approved, and the wildlife channel-numbers box hidden for history.
    - Create form: "Write the script from this research".
  - Tests: `tests/test_history_director.py` (16): style routing, wildlife unchanged, schema not mutated, research linking (approved vs edited), old plans loading, hook scoring, the script writer (invented ids, unsourced claims, inferred ids, flat hook), topic → script → Short via the API, approve → plan link. Full suite: 496 passed; tsc and eslint clean.
  - Live check (real Gemini, scratch library), Voynich Manuscript topic: 9 claims → approved → script → Short directed into 10 shots with origins (evidence/context/graphic) and a payoff scene. The pre-render check flagged the first script's flat hook ("This 15th-century codex contains…"). After the prompt fix and the claim-id fallback, the rewritten script opens "Why has this text never been reliably deciphered?" and links claims in every scene. The Director panel showed claims with sources and no wildlife numbers.
  - Open (for H4): the Director's footage searches are often generic ("ancient manuscript pages botanical"); searches that always name the entity, place and period, and routing history Shorts to archive sources, are H4's scope. The hook judge is a rule of thumb: it can't tell whether a question is interesting, only that one is there.
- [x] **H4 — Archival Shorts Footage Integration** (2026-11-07)
  - Found in the code (spec 19.3): general and history Shorts searched footage kind "footage", which has no `by_kind` entry, so only `sources` (Pexels, Pixabay, Mixkit, Unsplash, Commons) were searched. **No archive provider ran for Shorts.** Also, every Internet Archive item was labelled "Public domain" whatever it was.
  - Routing (`shot_footage.sources`): history plans search Settings' `archival` list (default: archive, nasa, commons, met), then the general sources. Results are ordered by that priority before size, and the ranking prefers a pick that shows the real subject. Wildlife (`species`) and general plans are unchanged (tested).
  - Searches name the entity (`entities` + `anchored`): when a shot's subject names a known entity (from the title, narration and the Director's subjects/places) and its first search doesn't, "<entity> <first words>" and the bare entity go first. Context and graphic shots keep their own searches.
  - History visual check (`look(..., history=True)`): Gemini also scores `period` (wrong era → match "weak") and `specific` (the actual named subject vs a lookalike), and gets the shot's factual requirements.
  - Provenance on every pick and alternative (`Footage.asset_type` own/graphic/archival/museum/photograph/stock, `depicts` actual/illustrative/unknown, `rights` licensed/rights_unknown, `period_score`). All default empty, so old plans load.
    - Stock is always illustrative.
    - "actual" needs both Gemini's `specific` ≥ 7 **and** the item's own record (title or page) naming the entity. In the live run Gemini took a Met facsimile of the Epistles of Clement for the Voynich Manuscript.
    - Source page, author and licence were already kept on `Footage` and in the record beside each downloaded file, which is where `post.txt` credits come from, so they survive picking, swapping and assembly.
  - Internet Archive (`archives.archive_licence`): the licence comes from the item's own `licenseurl` (Public Domain Mark, CC0, CC BY...), and the author from `creator`. Without one the item is "Rights not stated (Internet Archive item)", which counts as `rights_unknown`. This also applies to long videos' archive clips; their credit line now says what the item states.
  - Warnings: on the shot ("doesn't state a licence: check <page>", "stands in for <subject>: illustrative, not the real thing", "the period may be wrong") and in the pre-render check (`history.rights.*` under rights, `history.visual.*` under visual; history plans only). Director panel: "rights unknown", "the real subject" and "illustrative" chips, plus the asset type.
  - Tests: `tests/test_history_footage.py` (9): archive-first routing and entity searches, wildlife and general routing unchanged, authentic beats sharper stock, wrong period and lookalikes rejected, a stock fallback never authentic, rights_unknown flagged (shot and pre-render check), IA licences, old footage loading. Existing footage, credit, Director and plan-render tests unchanged and passing. Full suite: 505 passed; tsc and eslint clean.
  - Live check (Voynich Short, real Gemini and archive APIs):
    - The Met, Commons, Mixkit and Pixabay were all searched.
    - The history check rejected a jade carving and an East Asian painting (subject 0, period 0).
    - Picks marked as the real subject: Commons "Voynich manuscript (head).jpg" and "Beinecke Library Highsmith.jpg".
    - Stock and lookalike picks were labelled illustrative with warnings; the record-names-the-entity rule came from this run.
    - Unsplash answered 403 and NASA was unreachable that day; both failed per search with a log line, and the search carried on.
  - Open:
    - The Met answers one request per object, so it is slow on every shot, even "library exterior". The archival list is editable in Settings.
    - Period judgements can be wrong. The 2009 radiocarbon lab footage was marked "wrong era" because the shot didn't say the test was modern. It's a warning, not a removal.
    - The long-video storyboard page doesn't show asset type or rights yet (the Director panel does, for both formats).
- [ ] H7 core — minimum claim/source/rights gates
- [ ] H5 — Historical Map Animator
- [ ] H6 — Reconstruction and Motion Graphics
- [ ] H7 — full Preflight and Quality Inspector
