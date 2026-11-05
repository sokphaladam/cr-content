# CR Content — Attention Engine & Professional Editor Roadmap

**Target repository:** https://github.com/sokphaladam/cr-content  
**Target branch:** `main`  
**Document type:** Product and implementation roadmap  
**Primary scope:** Short mode first  
**Created:** 2026-11-05

---

## 1. Product vision

Turn CR Content from a script-to-video generator into an AI-directed short-form video production studio.

The creator should be able to paste a finished script and let CR Content:

1. Understand the story and why a viewer should keep watching.
2. Build a coherent Setup → Tension → Payoff narrative.
3. Direct purposeful shots and select footage that supports the narration.
4. Add suitable motion graphics, captions, transitions and sound design.
5. Assemble the edit in a professional, controllable workspace.
6. Preview the complete result, inspect it and render an upload-ready video.

The creator remains in control. The AI does repetitive directing and editing work, while important decisions stay visible, editable and reversible.

> **Product promise:** Make every second earn the viewer's attention. Do not promise that a video is impossible to skip, guaranteed to go viral, or guaranteed to achieve a particular retention rate.

## 2. Product principles

1. **Earn attention, do not trick viewers.** Curiosity, anticipation and surprise must be paid off honestly.
2. **Story before effects.** A strong story with restrained editing is better than a weak story covered in transitions and sound effects.
3. **Every shot has a job.** A shot must add information, evidence, emotion, context or a meaningful visual change.
4. **Do not confuse speed with retention.** Fast cuts are useful when they clarify or intensify a moment; unnecessary cuts create noise.
5. **Keep facts and footage honest.** Never imply illustrative footage proves an action, experiment or historical event.
6. **Preserve the creator's script.** Recommendations may be offered, but narration is not rewritten without explicit approval.
7. **Make editing understandable.** Automatic decisions should be inspectable and easy to override.
8. **Reuse working systems.** Extend the current AI Director, Director Plan, FFmpeg pipeline, GPU effects, Remotion runtime, timeline and quality tools. Do not build a parallel editor or renderer.
9. **Local-first and cost-conscious.** Keep core editing and rendering local. AI assistance should use the existing configured provider and degrade gracefully when unavailable.
10. **Protect existing workflows.** Deliver and validate Short mode first. Preserve Lyric Studio and other retained workflows; do not casually change their output or behavior.

---

## 3. Repository baseline and reusable foundations

This roadmap is based on inspection of the current `main` branch. These are existing foundations, not a claim that every proposed improvement is already implemented.

| Area | Existing files / components | Current foundation |
|---|---|---|
| AI story and shot planning | `crcontent/ai_director.py`, `crcontent/director_plan.py` | Whole-script direction, hook, central idea, emotional arc, payoff, scene purpose, emotion, continuity and shot plans |
| Footage selection | `crcontent/shot_footage.py`, `crcontent/plan_render.py` | Per-shot searches, candidate scoring, evidence requirements, alternatives, warnings and assembly |
| Short render and pacing | `crcontent/pipeline.py`, `crcontent/pacing.py`, `crcontent/render.py` | Word-timed impacts, reframing, B-roll, FFmpeg composition and audio mix |
| Image motion and effects | `crcontent/fx.py` | GPU camera movement, depth-based parallax, particles, atmosphere and image treatments |
| Sound effects | `crcontent/sfx.py` | Synthesized impact, whoosh, thunder and ambience beds for rain, wind, water and birds |
| Captions | `crcontent/captions.py`, `crcontent/styles.py` | Word-highlight captions, headline styles, positioning and presets |
| Preview and editing | `frontend/components/Storyboard.tsx`, `SceneCard.tsx`, `LivePreview.tsx` | Scene editing, footage selection, draggable text, caption preview and controls |
| Timeline | `frontend/components/Timeline.tsx` | Scene filmstrips, voice waveform, B-roll and text tracks with drag/trim behavior |
| AI Director UI | `frontend/components/DirectorPlanPanel.tsx` | Direct/re-direct, shot editing, footage search, alternatives and locking |
| Quality checks | `frontend/components/PreviewInspector.tsx`, `frontend/components/QualityInspector.tsx`, `crcontent/quality.py` | Preview checks and final-file technical/visual/audio inspection |
| Motion graphics | `remotion/src/Fact.tsx`, `MapZoom.tsx`, `SizeCompare.tsx`, `crcontent/shorts/motion.py` | Existing Remotion compositions rendered as transparent overlays for selected Short beats |
| Desktop packaging | `scripts/build_remotion.py`, `src-tauri/` | Bundled Remotion renderer and Node runtime for the desktop app |

### Important gaps to address

- The Director Plan describes the hook, emotional arc and payoff, but its scene model does not yet standardize explicit Setup/Tension/Payoff phases and attention roles.
- Some existing pacing and impact rules are keyword-driven. They need to become story-aware, not simply more aggressive.
- The existing motion-graphics set is useful but limited. It is not yet a broad, creator-editable graphics library with dedicated timeline clips.
- The existing timeline has scene, B-roll and text tracks. It needs a consistent overlay/graphics and independent sound-effect editing model.
- The current editor is capable, but scene cards and separate panels do not yet provide the integrated professional workspace described in this roadmap.
- The final quality report explicitly leaves storytelling checks such as hook, pacing and payoff unimplemented/not yet checked. Integrate real story checks without creating a second inspector.

### Existing specifications to build on

The repository already contains:

- `docs/AI-DIRECTOR.md` — AI Director and Script-to-Cinematic Video specification.
- `docs/CR-CONTENT-SHORTS-RETENTION-CINEMATIC-QUALITY-DIRECTOR-IMPLEMENTATION-PROMPT.md` — Shorts retention and quality inspection plan.
- `docs/CR-CONTENT-VIDEO-QUALITY-INSPECTOR-IMPLEMENTATION-PROMPT.md` — two-stage quality inspection specification.

Read these before implementation. Treat them as related specifications, reconcile overlap and update them only when necessary. This roadmap coordinates the work; it must not create duplicate AI Directors, quality inspectors or render engines.

---

# Part A — Attention Engine and Story Retention

## 4. The storytelling model

The default narrative foundation is:

**Setup → Tension → Payoff**

The AI may use additional beat roles inside those phases. These are narrative functions, not rigid time slots.

| Phase | Purpose | Possible beat roles |
|---|---|---|
| Setup | Interrupt the scroll, establish the subject and create a reason to watch | Pattern interrupt, striking image, curiosity gap, opening question or promise |
| Tension | Develop the question, establish stakes and increase anticipation through new information | Stakes, evidence, escalation, complication, contrast, mini-payoff, delayed reveal |
| Payoff | Deliver the promised answer or transformation and leave a satisfying final impression | Final reveal, explanation, emotional payoff, callback, natural loop |

A 25-second Short may use only a few beats. A 40-second Short may need more development. The AI must adapt to narration length and story complexity rather than forcing every video into identical timestamps.

### 4.1 Attention principles

The AI Director should evaluate and use these techniques when they fit the actual subject:

- **Pattern interrupt:** Open with an unusual, powerful or immediately relevant image/action, not a generic introduction.
- **Curiosity gap:** Raise a specific question the video genuinely answers.
- **Open loop:** Make the viewer aware of something they do not yet know; track it until it is resolved.
- **Stakes:** Explain why the question, behavior or discovery matters.
- **Escalation:** Each new beat should add evidence, increase consequence, complicate the question or change the viewer's understanding.
- **Mini-payoff:** Deliver a smaller discovery before the final answer, without giving away the main payoff too early.
- **Delayed reveal:** Hold back the key answer only when the delay adds meaningful anticipation.
- **Emotional contrast:** Use changes such as surprise → concern → wonder when supported by the story.
- **Callback / loop:** Connect the ending to the opening naturally. Do not force an unfinished sentence or misleading loop.

Do not apply every technique to every script. A straightforward educational fact may need a crisp question and answer, not artificial danger or manufactured suspense.

## 5. Extend the existing Director Plan

Extend `director_plan.py` and `ai_director.py`; do not introduce a second story-planning model.

### 5.1 Proposed plan fields

The exact schema must be designed after reviewing all current consumers and migration behavior. The following is a conceptual target:

| Field | Purpose |
|---|---|
| `phase` | `setup`, `tension` or `payoff` |
| `beat_role` | Pattern interrupt, curiosity gap, stakes, escalation, mini-payoff, final payoff or callback |
| `viewer_question` | What question should be active in the viewer's mind at this point? |
| `open_loop_ids` | Which specific questions/promises are introduced or still unresolved? |
| `resolved_loop_ids` | Which earlier questions are answered by this beat? |
| `tension_score` | Relative narrative tension/anticipation from 0–100; not an objective psychological measurement |
| `emotional_goal` | Intended viewer emotion, with a short reason |
| `payoff_reference` | What this beat contributes to the eventual payoff |
| `attention_reason` | Why this beat is worth watching; what new value it adds |

Preserve existing scene purpose, viewer objective, emotion, story, continuity and shot details. Avoid duplicated or contradictory fields.

### 5.2 Director behavior

The whole-script pass should:

1. Read and understand the complete narration before planning the first scene.
2. Identify the central promise/question and the final payoff.
3. Split the narration into purposeful beats without rewriting it.
4. Assign phases and beat roles.
5. Track open loops from introduction to resolution.
6. Check that every escalation adds new information or evidence.
7. Place mini-payoffs and the final payoff at appropriate points.
8. Identify weak, repetitive, confusing or unearned beats.
9. Direct shots that visibly support each narration line.
10. Plan a natural ending or callback when the story supports one.

A re-plan of one scene must preserve the global story, earlier/later dependencies, locked footage and user edits. If a local change breaks an open loop or payoff, warn the creator rather than silently changing unrelated scenes.

### 5.3 Script improvement behavior

- Keep the original narration as the default, immutable source.
- Offer specific alternative hook, transition or payoff lines as suggestions.
- Explain why each suggestion improves clarity, curiosity or payoff.
- Let the creator compare and explicitly accept/reject a suggestion.
- Never replace accurate context with exaggerated claims, false danger or unsupported promises.
- Preserve language behavior, including English and Khmer.

## 6. Story Retention Inspector

Integrate story checks into the existing Retention & Quality experience and the existing Preview/Final Quality reporting flow.

### 6.1 Pre-render editorial checks

At minimum, assess:

- Opening has an immediate, relevant reason to watch.
- The opening question/promise is specific and answerable.
- Setup establishes enough context to understand the tension.
- Every open loop is tracked.
- Tension/escalation adds new information instead of repeating the same fact.
- There are no unnecessary explanations or scenes that do not serve the story.
- The payoff answers the opening promise.
- The ending feels complete or loops naturally.
- Visual direction supports what the narration claims.
- The story is plausible and factually honest.

### 6.2 Finding quality

Each finding should include:

- Severity and category.
- Scene or timestamp, where available.
- The specific evidence that triggered the finding.
- Whether it is deterministic, heuristic or AI-assisted.
- A plain-language explanation.
- A concrete suggested fix.
- An explicit distinction between a verified issue and an AI recommendation.

Use scores as editorial guidance, not as a prediction of views or retention. A high score must not mean "guaranteed viral."

### 6.3 Channel analytics

Reuse existing Shorts analytics and the AI Director's channel evidence when sufficient data exists. Treat analytics as evidence, not rules. Do not overfit a small number of videos or force the same winning hook format onto every subject.

---

# Part B — Professional Video Editor

## 7. Editor experience and workspace

Redesign the editing experience as one coherent desktop-first workspace, while keeping the current Next.js/TypeScript architecture and shared UI system.

The editor should have four resizable/collapsible areas:

1. **Media & Assets panel — left:** project footage, imported media, music, sound effects, graphics templates and saved assets.
2. **Preview monitor — center:** playback, scrub, safe zones, selection handles, graphics/text manipulation and frame-accurate feedback.
3. **Properties inspector — right:** context-sensitive properties for the selected scene, clip, graphic, caption or audio item.
4. **Multitrack timeline — bottom:** video, B-roll, graphics, captions/text, voiceover, music and sound-effect lanes.

### 7.1 UX requirements

- Provide a clear selection model: selecting a timeline item selects the same item in the preview and properties inspector.
- Keep common actions discoverable: split, trim, delete, duplicate, undo, redo, zoom and fit timeline.
- Support drag/drop, snapping, playhead markers, keyboard shortcuts and accessible controls.
- Make panels resizable and collapsible; preserve sensible defaults for smaller displays.
- Keep preview controls, timeline and inspector visually consistent.
- Use the existing styling system and components where practical. Do not introduce a new component framework without a demonstrated need.
- Do not turn the first screen into a wall of technical controls. Advanced properties belong in the inspector.
- Preserve the current script/scene editing workflow as a simple way to review and change the story.

## 8. Timeline model

Extend the existing timeline rather than replacing it.

### 8.1 Required tracks

| Track | Content |
|---|---|
| Video | Main scene footage and scene order |
| B-roll | Cutaway footage and inserts |
| Motion graphics | Remotion template instances and future animated overlays |
| Text / captions | Headlines, labels, callouts and timed text |
| Voiceover | Narration waveform and timing |
| Music | Background score and music clips |
| Sound effects | Impacts, whooshes, ambience and action-specific effects |

### 8.2 Editing behavior

- Independent clip selection, move, trim, split, duplicate and delete.
- Visible clip labels, thumbnails/waveforms and clear track identity.
- Start/end trim, source in/out, timeline position, duration, fades and gain where relevant.
- Snap to playhead, clip boundaries, markers and beat/word timing.
- Track mute/solo/volume controls for audio.
- Lock/hide tracks where useful.
- Undo/redo for all user-visible edits.
- Autosave and restore without losing project state.
- Keep existing B-roll/text timing behavior backward compatible.

Do not implement a full non-linear editor feature set in one milestone. Prioritize the actions needed to place, trim, preview and refine Short-form edits.

## 9. Context-sensitive properties inspector

The inspector should change based on the selected item.

**Video / B-roll:** source, in/out, crop/layout, position/focus, speed, opacity, color treatment, transition and audio handling.

**Motion graphic:** template, text/data props, position, scale, rotation, opacity, duration, entry/exit animation, accent color and safe-zone placement.

**Text / caption:** content, font, size, color, highlight, outline, box/shadow, placement, timing and animation preset.

**Sound effect:** asset, category, start, source trim, duration, gain, fade in/out, audition and ducking behavior.

**Music:** track, source trim, volume, fade, loop behavior and voice ducking.

Provide sensible defaults and presets. Expose keyframes only where they are genuinely needed; do not add a complicated animation graph to the first release.

---

# Part C — Motion Graphics and Visual Polish

## 10. Extend the existing Remotion graphics system

The repository already uses Remotion for transparent graphics overlays and bundles its runtime for the desktop app. Reuse that infrastructure.

Existing compositions include:

- **Fact** — animated numeric fact.
- **MapZoom** — animated map location reveal.
- **SizeCompare** — animal/object size comparison.

The Short pipeline already has a Remotion integration in `crcontent/shorts/motion.py`. Audit this integration before changing it.

### 10.1 Initial template library

Prioritize reusable templates that explain or emphasize the story:

| Template | Use |
|---|---|
| Kinetic title | Short hook/title and section headline |
| Word emphasis | Highlight a key spoken word or short phrase |
| Fact / statistic | Number counter, unit and source/context label |
| Callout | Arrow, circle, pointer, label or annotation |
| Freeze-frame spotlight | Pause a meaningful frame and direct attention to a subject |
| Lower third | Subject, species, location or short explanatory label |
| Size comparison | Existing template; improve controls and preview |
| Map / location reveal | Existing template; improve controls and preview |
| Timeline / sequence | Explain a short sequence of events |
| Split-screen comparison | Compare two subjects, sizes, actions or states |
| Progress / process graphic | Show steps or a sequence without inventing data |

### 10.2 Template behavior

Each graphic should be a versioned, typed template instance with:

- Stable instance ID and template ID/version.
- Start time and duration.
- Validated template props.
- Position, size, rotation and opacity.
- Entry/exit animation preset and timing.
- Layer order.
- Optional accent/brand style.
- Preview thumbnail or representative frame.

Templates must render with transparent backgrounds and composite over the selected footage. Keep captions and critical UI-safe areas clear. Do not burn important text into the footage if it needs to remain editable.

### 10.3 Motion design rules

- Animation should support the meaning of the beat.
- Use motion hierarchy: one primary animated element at a time.
- Prefer clean easing, readable typography and purposeful movement.
- Avoid random particles, flashes, shake and zoom on every cut.
- Use strong movement for meaningful emphasis; use restrained movement for explanations.
- Keep graphics inside platform-safe areas and avoid covering the subject or essential footage details.
- Provide reduced-motion/low-effects options and allow creators to disable any generated effect.
- Ensure text and motion graphics remain legible at phone size and support the project's language.

## 11. Preview/render parity

Preview and final export must represent the same composition.

- Use the same template props, timings, placement, safe-zone calculations and animation parameters.
- Avoid a preview that looks correct but renders with different fonts, positions, scaling, or timing.
- Where live Remotion preview is too expensive, provide a cached representative frame or low-resolution preview and clearly indicate its status.
- Invalidate cached previews when their source footage, template, props, or timing changes.
- Keep transparent overlays, fonts and bundled assets compatible with the packaged desktop runtime.
- If a graphic fails to render, report the failure and provide a documented fallback; do not silently claim it was included.

---

# Part D — Sound Design

## 12. Upgrade the existing SFX pipeline

The repository already synthesizes several sound effects and mixes effects with voiceover and music. Extend the existing `crcontent/sfx.py` and audio finalization flow rather than creating a second mixer.

### 12.1 Sound library categories

| Category | Examples | Typical story use |
|---|---|---|
| Impact | Soft hit, cinematic thud, boom, crack | Important reveal or visual emphasis |
| Transition | Whoosh, riser, reverse swell | Intentional transition or build |
| Suspense | Low drone, heartbeat-like pulse, subtle tension swell | Build anticipation when appropriate |
| Nature / ambience | Forest, wind, rain, water, birds | Establish location and atmosphere |
| Animal / action | Wing flap, footsteps, movement, calls | Support a visible action; must match the subject |
| Reveal | Short tonal accent, impact, sparkle | Payoff or discovery |

Any downloaded sound library must have a known license and stored attribution/usage metadata where required. Prefer original synthesized sounds or appropriately licensed local assets. Do not make a paid sound service mandatory.

### 12.2 Sound direction rules

The AI Director should propose sound events with:

- Exact beat/shot reference and timeline time.
- Sound category and asset identifier.
- Intended emotional purpose.
- Duration and relative gain.
- Fade in/out.
- Whether the event should duck music.
- Whether the event is essential or optional.

Do not add a sound to every word or cut. Sound should emphasize meaningful story moments.

### 12.3 Audio mixing and safety

- Voiceover remains intelligible and takes priority over music and effects.
- Use existing music ducking as a foundation; refine attack/release and per-track controls.
- Add fades to prevent clicks and abrupt starts/stops.
- Avoid clipping and excessive low-frequency impacts.
- Preserve stereo/mono compatibility and handle missing audio gracefully.
- Respect the existing loudness/true-peak quality checks; tune targets based on the actual delivery profile rather than relying on a single arbitrary value.
- Do not let sound effects imply an action that the footage does not show.

---

# Part E — Integrated Automatic Editing

## 13. Emotional editing direction

The AI should map story intent to editing decisions. A phase is not itself an effect preset: different stories need different treatments.

| Story intent | Visual direction | Sound direction |
|---|---|---|
| Curiosity | Strong opening image, clean framing, restrained text | Short accent or purposeful near-silence |
| Investigation | Detail shots, evidence inserts, controlled camera movement | Subtle ambience, restrained pulse |
| Rising tension | More purposeful shot changes, tighter framing, stronger contrast in rhythm | Gradual swell; avoid constant impacts |
| Key action | Show the actual action clearly; use slow motion only when source footage supports it | Action-matched sound, with voice clarity preserved |
| Explanation | Stable composition, readable callouts/diagram | Reduce effects so information is clear |
| Payoff | Hold the reveal long enough to understand it; emphasize the decisive visual | Release tension, one meaningful accent or brief silence |
| Callback | Reuse an opening visual or phrase when it genuinely completes the story | Echo or resolve the opening sound motif |

### Automatic editing rules

- Prioritize footage that shows the exact narrated action when the script claims an action occurred.
- Distinguish exact-action evidence, correct subject, supporting footage and illustrative footage.
- If matching footage is unavailable, use an honest alternative (graphic, explanatory label, different shot or a warning); do not fabricate evidence.
- Avoid repeating the same shot, framing, transition or sound effect without purpose.
- Use source-aware slow motion; do not invent frames or imply a speed the footage cannot support.
- Let the editor change or disable every automatic decision.
- Keep user-selected and locked media protected during re-planning.

---

# Part F — Implementation Milestones

## 14. Delivery strategy

Deliver the roadmap in small, testable milestones. Do not begin with a complete editor rewrite. Start by improving story quality, then build the editor architecture needed to expose and control the richer edit.

### M0 — Repository audit and integration contract

**Goal:** Confirm the exact current implementation before adding overlapping models or state.

Tasks:

- Read this roadmap and the three related docs named in Section 3.
- Trace the Short flow from script input through Director Plan, voice timing, footage selection, preview, timeline, render, SFX mix and final inspection.
- Trace Remotion composition creation, render, caching, transparent overlay compositing and packaged runtime.
- Trace current draft schema, persistence, IDs, migrations and undo/redo support.
- Identify how the existing timeline calculates scene-relative and video-global time.
- Establish preview/render parity constraints and memory/performance limits.
- Run baseline backend tests, frontend type/lint checks and build checks. Record pre-existing failures honestly.
- Produce a concise file/API/schema map and implementation sequence.

**Acceptance criteria:**

- No new implementation duplicates an existing module.
- All shared data consumers and migration risks are identified.
- Baseline tests/build results are recorded.

### M1 — Attention Engine and Story Beat Model

**Goal:** Improve generated stories and beat-level direction without changing the editor layout yet.

Tasks:

- Extend the existing Director Plan schema with explicit phase and beat-role information.
- Add open-loop introduction/resolution tracking.
- Add tension progression and emotional-goal metadata.
- Update the existing AI Director prompt/schema and validation.
- Add story-aware checks for weak hooks, repeated information, missing stakes, unjustified escalation, unanswered open loops and unearned/missing payoff.
- Preserve script text and user-locked shots.
- Update schema version/migration behavior after auditing all stored plan formats.
- Update frontend TypeScript types and show phase/beat roles in the current Director Plan UI.
- Keep old saved plans loadable.

**Acceptance criteria:**

- A valid Short plan has an intelligible beginning, development and payoff, or explicitly reports why a different structure fits better.
- Open loops introduced by the plan are resolved or reported as intentionally unresolved.
- Tension progression is not forced to increase monotonically; quiet beats and relief are allowed.
- Re-directing one scene does not corrupt the whole story or overwrite locked content.
- Existing plans migrate and load without data loss.
- Unit tests cover schema defaults, migration, plan validation and open-loop logic.

### M2 — Story Retention Inspector

**Goal:** Give actionable editorial feedback before render, using the existing quality workflow.

Tasks:

- Implement deterministic checks wherever timing, text and plan structure provide enough evidence.
- Add AI-assisted semantic review only through existing provider configuration and explicit user action/permission consistent with current behavior.
- Reuse the existing finding/report model and inspector components.
- Connect findings to scenes, timestamps, preview and timeline.
- Clearly label deterministic, heuristic, AI-assisted, inferred and not-checked states.
- Offer suggested fixes without silently rewriting scripts or replacing footage.
- Keep reports tied to the correct draft revision and mark stale reports outdated.

**Acceptance criteria:**

- The inspector catches a missing/weak opening, unresolved story promise, repetitive escalation and payoff mismatch in representative fixtures.
- Findings explain their evidence and offer a concrete revision.
- False certainty is avoided; unsupported checks remain not-checked.
- Existing technical quality inspection remains functional.
- The feature works when optional AI services are unavailable.

### M3 — Professional Editor UX Foundation

**Goal:** Make the current editor feel like one coordinated editing workspace.

Tasks:

- Audit current page state, component boundaries and editor navigation before changing layout.
- Establish a single selection model for scene/clip/graphic/audio items.
- Reorganize the workspace into Media & Assets, Preview, Properties Inspector and Timeline regions.
- Add resizable/collapsible panels with appropriate desktop and narrow-window behavior.
- Add clear selection, focus, loading, empty, error and unsaved states.
- Keep scene/story editing discoverable and do not hide the simple paste-script workflow behind advanced controls.
- Reuse the existing UI system. Avoid replacing working components solely to adopt a new framework.

**Acceptance criteria:**

- Selecting a scene or existing timeline item consistently updates preview and properties.
- Current Short workflows remain usable without a new learning burden.
- No existing feature becomes inaccessible due to the redesign.
- Keyboard navigation, focus states and usable small-window layouts are verified.

### M4 — Multitrack Timeline and Editing Model

**Goal:** Extend the current timeline to support graphics and independent sound effects.

Tasks:

- Define a normalized, versioned timeline item model with stable IDs, track IDs, source in/out, timeline start, duration, layer order and typed properties.
- Preserve existing scene/B-roll/text data and provide backward-compatible migration/adapters.
- Add motion-graphics and SFX tracks first; do not destabilize the current scene timeline.
- Add select, move, trim, split, duplicate, delete, snap and undo/redo for the supported item types.
- Add audio waveforms, track mute/solo/volume and fades.
- Add track locking and visibility controls where useful.
- Ensure time calculations work for scene-relative items and timeline-global items.
- Persist edits safely and restore the same timeline after app restart.

**Acceptance criteria:**

- A creator can add, move, trim and delete a graphic and SFX clip independently.
- Preview and render use the same timing.
- Undo/redo restores all supported item properties.
- Existing B-roll/text and voiceover workflows remain intact.
- No timeline item is lost during save/reload or schema migration.

### M5 — Motion Graphics Template Library

**Goal:** Expose the existing Remotion renderer as an editable, reusable graphics system.

Tasks:

- Define typed, versioned template definitions and validated instance props.
- Refactor existing Fact, MapZoom and SizeCompare compositions only as needed to fit the common contract.
- Add the first new templates: kinetic title, callout/arrow/circle, lower third, freeze-frame spotlight, split comparison and simple process/sequence graphic.
- Build an asset/template browser with thumbnails and short descriptions.
- Add inspector controls for text/data, accent color, position, scale, timing and entry/exit presets.
- Place instances on the timeline graphics track.
- Add preview caching/invalidation and render transparent overlays using the existing Remotion pipeline.
- Verify bundled desktop Node/Chrome/runtime behavior and packaged assets.

**Acceptance criteria:**

- Templates can be inserted, edited, moved, trimmed and removed.
- Props are typed and validated; invalid data results in a visible error.
- Preview and final render match within documented limitations.
- Existing Remotion graphics continue to render.
- A missing/failed optional graphic never silently disappears without a warning.
- No new mandatory cloud dependency is introduced.

### M6 — Sound Design Library and Audio Timeline

**Goal:** Let AI and creators place meaningful sound effects as editable timeline clips.

Tasks:

- Extend the existing SFX system and mixer; do not introduce a second audio engine.
- Add a local asset catalog with category, duration, source, license/attribution and preview metadata.
- Include synthesized effects and optional imported/licensed user assets.
- Represent every editable effect as a stable timeline item with trim, start, duration, gain and fades.
- Add preview audition, track mute/solo and music/voice ducking controls.
- Let the AI propose sound events tied to story beats and shots.
- Add audio normalization/true-peak validation using existing quality tooling.

**Acceptance criteria:**

- Sound effects can be inserted, previewed, moved, trimmed, faded and removed.
- Narration remains clearly intelligible.
- The final mix has no clipping or unintended clicks.
- Missing optional effects do not stop video rendering.
- License/attribution information is retained for imported assets where required.

### M7 — Story-Aware Editing Director

**Goal:** Connect narrative purpose to automatic shot, graphics and sound decisions.

Tasks:

- Map phase/beat role to shot size, camera movement, cut rhythm, graphic treatment and audio suggestions.
- Keep exact-action footage requirements higher priority than decorative effects.
- Use mini-payoffs and key evidence as candidate moments for selective emphasis.
- Place graphics only where they clarify the story.
- Reduce effects during explanations, serious moments or when they compete with narration.
- Avoid repeated templates, repeated SFX and monotonous shot rhythms.
- Provide an explainable reason for each automatic edit.
- Allow creators to approve, override, lock or disable AI suggestions.

**Acceptance criteria:**

- A sample Short has coherent story progression and visually/audio-supported beats.
- Automatic effects are selective and purposeful.
- User edits and locked items survive re-directing.
- If footage/evidence is weak, the system reports the gap rather than hiding it with graphics.

### M8 — Quality, Performance and Regression Hardening

**Goal:** Verify the whole production result, not just isolated UI pieces.

Tasks:

- Add pre-render story checks to the existing quality flow.
- Add graphics/timeline/audio integrity checks.
- Verify rendered output with the existing final-file inspector.
- Add draft-to-render consistency checks for item timing, captions and overlays.
- Benchmark render time, peak RAM/VRAM, preview responsiveness and project save/load.
- Test low-resource configurations and operation without optional GPU/AI services.
- Verify packaged desktop builds on supported operating systems.
- Run full backend/frontend tests, lint, type checks, build and representative manual Short renders.
- Document limitations and recovery behavior.

**Acceptance criteria:**

- A complete Short can be created, edited, saved, reopened, previewed, rendered and inspected.
- The result matches the visible edit, within explicitly documented preview limitations.
- Existing Short and Lyric workflows pass regression tests.
- No unsupported feature is falsely reported as passed.
- Test and build results are recorded with actual commands and outcomes.

---

## 15. Suggested implementation order

The order below is intentional:

1. **M0 — Audit**
2. **M1 — Attention Engine**
3. **M2 — Story Retention Inspector**
4. **M3 — Professional Editor UX Foundation**
5. **M4 — Multitrack Timeline**
6. **M5 — Motion Graphics**
7. **M6 — Sound Design**
8. **M7 — Story-Aware Editing Director**
9. **M8 — Hardening**

Do not start M5/M6 before a stable timeline item model and preview/render contract exist. Otherwise, every graphic and sound feature will require another round of data migration and UI rework.

---

## 16. Testing strategy

### Backend

- Story phase/beat validation.
- Open-loop introduction and resolution.
- Payoff relationship and missing-payoff warnings.
- Plan schema migration and old-plan loading.
- Scene re-plan preserving locked shots and global story.
- Timeline serialization, normalization and migration.
- Graphic template props validation and render failure handling.
- SFX timing, gain, fades, ducking and empty/missing assets.
- Render composition and output duration.
- Quality findings and draft/render revision association.

### Frontend

- Selection synchronization between preview, timeline and inspector.
- Timeline add/move/trim/split/delete/duplicate.
- Undo/redo and autosave/restore.
- Resizable/collapsible panel behavior.
- Graphic template insertion and prop editing.
- SFX insertion, audition and property changes.
- Empty, loading, failure and stale-report states.
- Accessible keyboard interaction and narrow-window behavior.

### Rendered-media integration

Create deterministic fixture projects representing:

1. A short wildlife fact with an opening hook and factual payoff.
2. A suspenseful action sequence with a delayed reveal.
3. A straightforward educational explanation with no artificial suspense.
4. A Short with no optional GPU/AI graphics available.
5. A Short containing graphic overlays and multiple sound effects.
6. A Short with missing media or a failed optional graphic.
7. A project reopened after saving edits.
8. A regression fixture for Lyric Studio.

Verify video dimensions, frame rate, duration, audio stream, loudness/peak, caption timing, overlay placement and absence of accidental black/frozen sections. Inspect real rendered frames and listen to representative mixes; metadata checks alone are insufficient.

### Manual acceptance session

A creator should be able to:

1. Paste a prepared script.
2. Review the AI story phases and retention findings.
3. Accept or reject one suggested hook/payoff improvement.
4. Inspect and adjust a footage/shot choice.
5. Insert a motion graphic and edit its text/position.
6. Add a sound effect, adjust its timing/gain and hear it in context.
7. Save, close and reopen the project.
8. Preview the final edit.
9. Render and run the final quality inspection.
10. Confirm the exported video matches the approved edit.

---

## 17. Performance, reliability and compatibility requirements

- Do not decode or render full-resolution Remotion compositions on every timeline drag. Use lightweight/cached previews and render final quality only when needed.
- Cache previews by source asset, template version, props, timing and output settings. Invalidate cache on any relevant change.
- Keep rendering jobs cancellable and report progress/errors truthfully.
- Avoid holding multiple large decoded videos or GPU tensors unnecessarily.
- Release GPU/VRAM resources when a render stage finishes or fails.
- Make project writes atomic where practical; do not corrupt a project on interrupted saves.
- Keep timeline and Director Plan migrations explicit and tested.
- Keep current desktop packaging and bundled Remotion runtime operational.
- Avoid new mandatory paid APIs, hosted media services or cloud rendering.
- Preserve the existing Short render output settings unless a tested change is required.
- Protect Lyric Studio behavior with regression tests when shared code is modified.

---

## 18. Success measures

Use measurable product checks rather than promising platform outcomes.

### Story quality

- Share of generated Shorts with a clearly identified opening promise and payoff.
- Count of unresolved open loops and repeated-information findings.
- Editorial review findings accepted/rejected by creators.
- Creator-rated clarity and usefulness of story direction.

### Editing experience

- Time and number of actions required to make a common edit.
- Successful save/reopen and undo/redo rates.
- Preview responsiveness while scrubbing.
- Share of automatic edits creators keep versus override.

### Visual and audio quality

- Graphics/preview/render consistency.
- Render failures and optional-effect fallback rate.
- Audio clipping/peak failures and voice intelligibility.
- Creator-rated usefulness of motion graphics and sound design.

### Channel performance

Where the creator connects and supplies adequate YouTube analytics, compare retention and engagement with the channel's own previous videos of similar format and age. Treat this as observational evidence, not proof of causation. Do not claim an edit caused a performance change without a suitable evaluation design.

---

## 19. Non-goals

This roadmap does not authorize:

- A promise of guaranteed views, virality, watch time or monetization.
- Deceptive hooks, fabricated stakes, fake urgency or misinformation.
- Automatic rewriting or publishing without creator approval.
- Replacing the existing FFmpeg render engine.
- Building a second AI Director, story inspector, timeline or audio mixer.
- Replacing Remotion with another graphics renderer without a measured technical reason.
- Rebuilding all features of Premiere Pro, DaVinci Resolve or After Effects.
- Making a paid cloud service mandatory.
- Changing Lyric Studio's visual/audio behavior as part of the Short-first milestones.
- Expanding unrelated creation modes as part of this roadmap.

---

## 20. Coding-agent execution instructions

When using this document to implement the roadmap:

1. Work inside the existing repository and inspect the actual current branch before modifying code.
2. Read the related docs listed in Section 3 and reconcile requirements with the implementation already present.
3. Complete **one milestone at a time**, in the order in Section 15.
4. Before each milestone, list the exact files and contracts expected to change.
5. Do not assume this document's suggested fields or component names must be copied verbatim; adapt them to the actual code after auditing consumers.
6. Preserve backward compatibility and create explicit migrations where required.
7. Do not create placeholder UI or schema-only work and report the feature as implemented.
8. Add tests alongside each behavior; run targeted tests after each change.
9. Run the full relevant regression suite before declaring a milestone complete.
10. Keep the application buildable at each milestone. If a requirement cannot be completed safely, document the blocker and leave a coherent working state.
11. Do not silently modify generated assets, user projects, API keys, environment files or unrelated workflows.
12. Do not make destructive Git operations or overwrite user work.

### Required implementation report after each milestone

- Summary of completed behavior.
- Exact files added, modified or removed.
- Data/API/schema changes and migrations.
- Tests and build commands actually executed, with results.
- Manual test steps and evidence.
- Known limitations, performance impact and remaining work.
- Confirmation of regression checks for Short mode and Lyric Studio where relevant.

---

## 21. Definition of done for the overall roadmap

The roadmap is complete only when:

- The existing AI Director produces explainable, coherent story phases and beat roles.
- Open loops and payoffs are tracked and validated.
- The existing quality workflow gives useful, evidence-based story feedback.
- The editor provides a coherent professional workspace with synchronized preview, timeline and inspector.
- Graphics and SFX are editable timeline items, not hardcoded effects.
- Existing Remotion compositions and the expanded template library render correctly.
- Preview and export are consistent within documented limitations.
- Automatic editing is selective, story-aware and reversible.
- Creator edits and locked decisions survive save/reopen and AI re-planning.
- The complete Short workflow works on the packaged desktop app.
- Existing Lyric Studio behavior remains intact and regression-tested.
- Tests, type checks, lint, builds and representative rendered-media checks are completed and reported honestly.

**Final workflow target:**

**Paste script → Understand story → Direct beats and shots → Review retention → Assemble professional edit → Add graphics and sound → Preview → Render → Quality check → Creator-approved export.**

---

## Progress

- [x] **M0 — Audit** (2026-11-05). Plan schema: `crcontent/director_plan.py` (pydantic, `migrate()` on every load). Stored in `drafts/<id>/draft.json` ("plan") for Shorts, `<job>/plan.json` for Long. Written by `ai_director.direct()`, `PUT /api/plans/{kind}/{ref}` (`web.plan_update`) and footage search (`shot_footage`). Frontend types: `frontend/lib/api.ts` (`DirectorPlan`, `PlanScene`). Baseline: 395 backend tests pass; `tsc` and `eslint` are clean.
- [x] **M1 — Attention Engine** (2026-11-05). Plan v2: `Scene.phase / beat_role / viewer_question / opens / resolves / tension` and `Story.loops`. v1 plans load with these fields empty. Emotional goal and attention reason reuse the existing `emotion` / `purpose` / `viewer_objective` fields instead of duplicating them. Deterministic `director_plan.story_check()` is stored in `plan.story_warnings` and recomputed on every direct and every save. The AI Director prompt and schema ask for beats and loops. The Director Plan panel shows phase/role/tension/question per scene, the open questions and the story checks. A whole-video re-plan gives a scene with a locked shot its story beat too; its shots are kept. Verified: all 15 stored v1 plans in the library load as v2 with every value intact (read-only check); one real AI Director run on a 6-scene Short gave setup → tension → payoff, both open questions resolved, non-monotonic tension, no story warnings and the narration unchanged; 396 backend tests pass; `tsc` and `eslint` are clean. Left for later milestones: editing phases/loops in the UI (M3 inspector) and accept/reject script suggestions (5.3; not in M1's task list).
- [x] **M2 — Story Retention Inspector** (2026-11-05). Built into the existing pre-render check (`quality_preview.inspect_short`); there is no second inspector. The draft's Director Plan reaches it (`draft` on `POST /api/inspect/preview/short`). `director_plan.story_findings()` produces structured findings (scene, title with evidence, suggested fix), matched to the editor's scenes by narration so they carry a scene and timestamps and click through to the editor and timeline. Every preview check now has a `method`: measured / heuristic / inferred (rules over the AI Director's beats) / ai / not_checked, and the finding detail shows it. Plans without beats (script-seeded, or AI plans from before M1) report "not checked", not a warning. The plan is part of the report fingerprint, and the editor marks the report outdated when the plan changes. Repeats come from the existing `story.repeat` check only, not twice. The AI story and footage reviews are unchanged: on request only, now labelled `ai`. Verified: fixtures for a weak or missing opening, an unresolved promise, repetitive escalation and a payoff mismatch (`tests/test_story_inspector.py`); 12 real drafts checked read-only (11 pre-M1 AI plans → not checked, 1 script plan → not checked); a real AI-directed plan passes and, with its payoff broken, gives 2 findings with scene and time; 405 backend tests pass; `tsc` and `eslint` are clean. Not done: the final render report (`quality.py`) still lists storytelling as not checked; story checks there are M8's "pre-render story checks in the quality flow". The UI wasn't clicked through in a running app.
- [x] **M3 — Professional Editor UX Foundation** (2026-11-06). Audit: the editor already had the four regions (Project panel left, Preview centre, Inspector right, Timeline bottom), resizable remembered side panels, a stacked layout under 1024 px, and undo/redo. So M3 extends it instead of re-laying it out. Added:
  - **One selection** (`ItemRef` = scene + B-roll/text clip; owned by `app/page.tsx`). Clicking or pressing Enter/Space on a timeline clip, or pressing a text on the preview, selects it. The playhead moves to it, the preview outlines it (text) or frames it (B-roll), the inspector opens its scene with that clip highlighted and scrolled into view, and the timeline marks it (`aria-pressed`). Selecting a scene clears the clip. Clicking a voice-track segment selects its scene.
  - **Collapsible side panels:** toggles in the preview bar, folded to an icon rail whose icons reopen that tab, remembered per panel. A selection always reopens the inspector.
  - **Media tab** (Media & Assets): every footage file the draft uses, with buttons for each use that select that scene or clip.
  - Project tabs fit the default 300 px panel.
  - Files: `app/page.tsx`, `components/Storyboard.tsx`, `Timeline.tsx`, `LivePreview.tsx`, `SceneCard.tsx`, `lib/appearance.ts`. No backend or schema changes.
  - Verified in the running app on an isolated copy of one real draft (fake APPDATA): timeline text and B-roll selection syncs preview, inspector, Scenes and Media; Enter on a focused clip selects it, with a visible focus outline; panels fold, persist across reload and reopen on selection; the narrow layout (896 px frame) switches its Editor tab to Scene on selection and every tab is still reachable; no app console errors. `next build` (0 errors, 0 warnings), `tsc`, `eslint` and 405 backend tests pass.
  - Left for M4: music, SFX and graphics clips aren't selectable items yet; they don't exist as timeline items until M4.
- [x] **M4 — Multitrack Timeline and Editing Model** (2026-11-06).
  - **Model:** `script.Clip` (stable id, track `graphics`/`sfx`, global start, duration, source in, sound/template, props, gain, fades, layer) and `script.TrackState` (mute, solo, volume, locked, hidden) on `VideoScript.clips/tracks`, with `timeline_version = 1`. Ids are unique and track names are validated. Older scripts load with none. Scene B-roll and texts stay scene-relative, unchanged.
  - **Render** (`crcontent/timeline.py`): sound clips feed the existing `render.finalize` effects. The mixer now takes an optional trim/fade per effect (`atrim`/`afade`), and old 3-tuples still work. Graphics clips go through the existing `shorts.motion.overlay` (Remotion, transparent) over the joined picture. Lane mute/volume reaches the music level and a new `voice_gain`. Solo is preview-only by design. Anything left out (unknown sound or template, hidden lane, Remotion failure) is logged, never silent.
  - **Pre-render check** warns about clips that won't render, clips after the end, and missing Remotion.
  - **Engine:** `/api/timeline/catalog`, `/api/sfx/{name}.wav`, `/api/sfx/{name}/peaks`.
  - **Editor:** lane headers (M/S/volume for voice, music and sounds; hide/lock/add for graphics and sounds), graphics and sound lanes with select, move, trim both edges (a sound can't trim past its file), split at the playhead (S), duplicate to the next free gap (Ctrl+D), delete (Delete), arrow nudge, and snap to the playhead, scene cuts, word starts and other clip edges. Sound waveforms and fade shading, a music lane, and a clip inspector (sound/template, timing, source in, gain, fades, props, layer, audition). The preview plays sound clips in time under lane mute/solo/volume and shows where and when each graphic will be drawn. Undo/redo, autosave and restore come from the draft history; a shortcut key is now its own undo step.
  - **Verified:** `tests/test_timeline.py` (8, including a real ffmpeg mix: the trimmed sound is present only inside its window) and `lib/clips.test.ts` (8). In the running app on the isolated library: add, edit, move (snapped), trim, split, duplicate, delete, undo/redo, lane mute and a reload restoring the clips. One real render: the Remotion "7 hearts" graphic is absent at 4.8 s, present at 6.0 s and gone at 8.6 s (placed 5.15–8.15), and the impact's low-end energy sits at 11.8–12.3 s (placed 11.8 + 0.45). 413 backend tests, `tsc`, `eslint` and `next build` pass.
  - **Found and fixed while testing:** a duplicate could land on top of a split's second half; two shortcut keys within 0.7 s merged into one undo step.
  - **Limits:** the preview shows a labelled placeholder, not the real Remotion frame (cached previews are M5). Template props are free-form until M5's typed templates. Solo isn't applied to the render.
- [x] **M5 — Motion Graphics Template Library** (2026-11-06).
  - **Contract** (`crcontent/graphic_templates.py`): 9 typed, versioned templates (field type, default, limits, group) shared by the engine and the editor through `/api/timeline/catalog`. `validate()` fills defaults, drops unknown keys and reports problems in plain words, never clamping. `Clip.template_version` exists; a newer version is refused. Every graphic gets shared placement from `remotion/src/Placed.tsx`: `at_x`/`at_y` (not `x`/`y`, which Fact already uses in px), scale, rotation, opacity, and 6 entry/exit presets. With no placement props it is the identity, so Shorts mode's Fact, MapZoom and SizeCompare render exactly as before (verified: the Fact still draws around y=576).
  - **New compositions** (`remotion/src/Templates.tsx`): KineticTitle, Callout (circle/arrow/box), LowerThird, Spotlight (freeze-frame: the render passes the picture at the clip's start), SplitCompare and Process. Existing compositions were changed only by wrapping them in `placed()`.
  - **Preview frames:** `remotion/still.mjs` and `POST /api/graphics/stills` render transparent PNGs. They're cached by template, version, props and length, so any change makes a new frame. The source bundle is cached by a hash of `remotion/src`, and the desktop prebuilt bundle is used when present. Each item answers made, invalid (errors) or failed (reason). `build_remotion.py` ships `still.mjs`.
  - **Editor:** the Media tab gains a Graphics browser with real thumbnails and descriptions, adding at the playhead. The inspector is built from the spec: grouped Content/Style/Position/Motion fields (text with counters, number, colour, choice), an error under each bad field and a banner saying the render would leave the graphic out. The preview shows the real Remotion frame with a status chip ("Preview frame" / "Drawing…" / "Won't render: …" / "No preview: …"), stacked under the headline and captions like the render. Invalid graphics are left out of the render with a logged reason and flagged in the pre-render check.
  - **Verified:** `tests/test_graphic_templates.py` (9, including a real Remotion still with a measured alpha coverage), the updated `test_timeline.py`, and `lib/templates.test.ts`. All 9 templates rendered and checked visually. In the app on the isolated library: browser thumbnails, add, edit (the preview redrew), a cleared required field (errors shown, chip red, graphic hidden). A real render with Fact, LowerThird and Spotlight: render frames match the preview frames in place and look, and the spotlight holds the picture (frame difference 2.6 vs 71 on moving footage). The prebuilt bundle via `bundle.mjs` and `still.mjs` lists all 9 compositions. 422 backend tests, Remotion and frontend `tsc`, `eslint`, 15 frontend unit tests and `next build` pass.
  - **Found and fixed while testing:** the Fact went off-screen when its own `y` collided with the placement `y`; the preview drew graphics over the headline while the render puts text on top; Process previews showed only 2 of 3 steps.
  - **Limits:** the preview is one still frame (motion plays only in the render); the editor's Spotlight preview dims the live picture (the render freezes it); the full desktop installer build wasn't run.
- [x] **M6 — Sound Design Library and Audio Timeline** (2026-11-06). Extends `sfx.py` and the one mixer (`render._mix_audio`); no second audio engine.
  - **Library:** 12 synthesized sounds in the roadmap's 6 categories, with descriptions. New: riser, drone, pulse, chime, wing flap; all made locally with no licence needed, and the desktop build bundles them via `make_all`.
  - **Imports:** `POST /api/sfx/import` stores the file in `assets/sfx` with a JSON sidecar (label, category, licence, credit, source, duration). An unknown licence is refused, CC BY/BY-SA require a credit, and unreadable or over-120 s files are refused and not kept. Imported sounds are `user:<id>`, with ids checked against path traversal.
  - **Credits:** the render writes the credits licences ask for into `post.txt` and records every used sound with its licence in `meta.json`. A missing imported sound is logged and left out, never failing the render, and flagged in the pre-render check.
  - **Mix:**
    - `Clip.duck` makes a sound dip the music, added to the sidechain key.
    - `TrackState.duck` sets how far the music dips under the voice (0 to 1; ratio 1 + 5 × duck).
    - Timeline sounds are compressed under the voice for intelligibility, at most about 6 dB.
    - Every clip gets at least a 5 ms fade at both ends, so there are no clicks.
    - Mixes containing timeline sounds get 0.5 dB more limiter headroom; other Shorts and music videos are unchanged.
    - New fields: `Clip.essential`, `Clip.note`.
  - **Suggestions** (`crcontent/sound_director.py`, `POST /api/sounds/suggest`): Gemini proposes events from the plan's beats, shot sound notes and the library, when a key is set and the user opts in. Otherwise rules: ambience from the scenes' words; payoff chime plus a riser into it; a hit on evidence or a mini-payoff; a pulse on a delayed reveal. Both are checked (unknown scenes or sounds dropped, values clamped), spaced at least 1.5 s apart, capped at one accent per 6 s, and given a reason. Nothing is added until ticked; all ticked sounds are added as one undoable edit.
  - **Editor:** the Audio tab has a music-ducking slider, the suggestion list (essential ones pre-ticked), the library by category (audition, add at playhead) and the import form (credit becomes required for CC BY). The clip inspector has the sound list grouped by category with its licence and credit, "Dip the music", "Essential" and the suggestion's reason. The timeline shows library names, and the preview dips the music under ducking sounds.
  - **Verified:** `tests/test_sound_library.py` (9, including real ffmpeg mixes for ducking, the voice priority, a click-free cut and the true peak, plus the import rules, credits, rules and AI-checked suggestions with fallback); the M4 tests updated. In the app on the isolated library: audition, add, import (CC BY made the credit required; the sound joined the library with licence and credit), rule suggestions added and undone as one step. A real render with 5 sounds (imported CC BY, ducking): the credit is in `post.txt`, the licences are in `meta.json`, and the existing final inspector passes everything (true peak -1.4 dBTP, -14.1 LUFS, no jumps, balanced, mono-safe). Before the headroom fix it warned at -0.9 dBTP; pre-roadmap Shorts sat at exactly -1.0. A real Gemini suggestion on the M1 crow Short gave 4 restrained events with no action sounds the footage couldn't show and one essential, music-ducking chime on the retrieval. 431 backend tests, 15 frontend unit tests, `tsc`, `eslint` and `next build` pass.
  - **Limits:** the preview doesn't dip music under the voice (the render does); no listening test by ear; ambience beds are a fixed 5 s (an existing shortcut in `sfx.py`).
- [x] **M7 — Story-Aware Editing Director** (2026-11-06).
  - **`crcontent/edit_director.py`** (`POST /api/edit/direct`) turns the plan's phases and beat roles into proposals, each with a reason:
    - **Calm scenes:** explanation, context and relief scenes, plus the final payoff held. Never the hook.
    - **Graphics, only where they clarify:** the subject named once, early; a number the voice says in an evidence, stakes or payoff beat (unless the headline already shows it); a spoken sequence as steps. At most one per 8 s, never overlapping, the same template not again within 8 s.
    - **Sounds:** from the M6 sound director. The same accent is never repeated within 8 s, and nothing duplicates a sound the creator already placed.
    - **Evidence gaps:** an exact-action shot whose footage doesn't show the action is reported with what to do, and that scene gets no graphic or accent that would dress it up.
  - Plan rhythm warnings (repeated sizes, slideshow runs) are passed through. Plan scenes are matched to draft scenes by narration, falling back to position when a line was edited.
  - **Render:** `Scene.calm` ("auto" from the director, "on"/"off" from the creator) means only the marked words hit: no punchy-word or hook hit, no flash, 1.8× slower re-framing (`pacing.impacts(auto=False)`).
  - **AI Director prompt:** now maps story intent to shot choices (roadmap section 13), with exact action outranking pretty shots.
  - **Editor:** the Director tab has an Edit Director panel: gaps first, notes, tickable decisions, Apply as one undoable edit, and "Remove its edits". Applied clips have `origin: "director"`, and any change by the creator makes them `"edited"` (`clips.touched` via `replace`/`duplicateIn`/inspector), so re-planning replaces only untouched director clips and never a locked lane's. Each scene has a Calm toggle with the director's reason.
  - **Found and fixed while testing:**
    - **`toScript` bug:** it never sent `calm`, so neither the creator's choice nor calm pacing reached the engine or the render. (Note: `toScript` also omits `sound`/`speed`, which pre-dates this roadmap; left as is and reported.)
    - Plan/draft narration drift hid the scene-5 gap.
    - A water bed was proposed on top of the creator's identical one.
  - **Verified:** `tests/test_edit_director.py` (11) and `lib/editDirector.test.ts` (3). In the app on the isolated library, after a real AI re-plan and footage search: 2 real gaps reported (scenes 1 and 5, footage shows only the subject); calm proposals applied with reasons shown; the creator's "off" respected on re-run; the render received the calm values. The calm scene 4 had no automatic hits and B-roll, so its picture was correctly unchanged; with calm set on the hook scene, the render's boom at 0.6–0.8 s disappeared (low-end 1298 → 39) and the rest stayed the same. 442 backend tests, 18 frontend unit tests, `tsc`, `eslint` and `next build` pass.
  - **Limits:** the editor's preview doesn't show calm pacing (render-only, like the existing hits); the director's shot-size and camera mapping lives in the AI Director's prompt, not in deterministic rules.
- [x] **M8 — Quality, Performance and Regression Hardening** (2026-11-06).
  - **Draft-to-render consistency:** the Short render records in `meta.json` `timeline` which graphics it drew (at what time and length), which sounds it mixed, and why any clip was left out (`left_out`, filled by `timeline.sound_events`/`graphic_clips` and a Remotion failure). The existing final inspector (`quality.edit_checks`, Short profile) compares that with the video's `script.json`:
    - pass when every clip is in as placed;
    - a warning per clip left out, with the recorded reason and time range;
    - fail when a clip is missing without a reason, or drawn at another time or length;
    - not checked for renders made before the record existed.
  - **Story in the final report:** the draft's Director Plan story findings, so "Hook, pacing and payoff" is no longer just "not checked" when the plan has beats.
  - **Low-resource run** (engine with no Remotion and no Gemini key, an imported sound's file deleted):
    - Preview frames answer "failed".
    - Sound suggestions fall back to the rules.
    - The pre-render check warns about the missing sound and "Graphics can't be drawn on this computer".
    - The render still finished (48 s for 20.7 s of video).
    - The final report lists the 3 graphics and 1 sound left out with their reasons, and passes the 4 clips that were mixed.
  - **Benchmarks** (RTX 3060 12 GB, this PC):
    - Short render 42–48 s for 20.7 s of video; peak RAM of the engine plus its ffmpeg/node children 2.7 GB; VRAM +0 MB (stock clips: no GPU camera moves in this draft).
    - Preview frames: 9 templates in 14 s cold, including the first bundle; cached afterwards.
    - Draft with 30 scenes and 200 clips: save 3 ms, load 13 ms, 115 KB, exact round trip; quick pre-render check 28 ms warm.
  - **Regressions:** 448 backend tests (69 of them Lyric Studio / NeonMekong), Remotion and frontend `tsc`, 18 frontend unit tests, `eslint` on every changed file, and `next build` pass. A full-repo `eslint` still fails only in `OutlierFinder.tsx` and `PreviewPane.tsx`, with problems that exist on `HEAD` (not introduced here).
  - **Not done:** the packaged desktop installer wasn't built (it downloads Node and a headless Chrome); `build_remotion.py` now ships `still.mjs` and the engine build bundles the new sounds via `make_all`.

## Limitations and recovery (after M0–M8)

- **Preview vs render:**
  - Graphics preview as one still frame from Remotion (motion only in the render).
  - The spotlight dims the live picture in the editor; the render freezes it.
  - The preview dips music only under "dip the music" sounds, not under the voice.
  - Calm pacing and automatic hits exist only in the render.
- **Recovery:**
  - A graphic Remotion can't draw, an invalid graphic, or a missing sound never stops a render. It's left out, logged, recorded in `meta.json` and reported by the final inspector.
  - Without a Gemini key, the AI story review, AI sound suggestions and AI Director are unavailable; the rule-based checks and suggestions still work.
  - Every editor change, including applying Edit Director proposals or sound suggestions, is one undo step.
  - Re-planning keeps clips you changed and locked lanes.
- **Field-dropping finding (pre-roadmap):** the editor's `toScript()` drops scene `sound`, `speed` and `impacts` that the Director Plan's assembly writes into the draft. The editor's renders never get the plan's cut sounds or slow motion. A render made from the stored draft through the API does get them: in testing that render alone had scene-start impacts, which the inspector flagged as 14 LU jumps out of pauses. `impacts` there also holds beat labels ("Visual hook"), not words. Left unchanged because fixing it changes how existing videos render; needs a decision.
- **Not verified:** the packaged desktop installer; listening tests by ear; a Lyric Studio render (covered by its 69 tests only, and its mix path is unchanged: the soundtrack branch of `_mix_audio` and the default limiter are untouched when no timeline sounds are present).

## Definition of done: status

| Item (section 21) | Status |
|---|---|
| Explainable story phases and beat roles | Done (M1), checked with live AI runs |
| Open loops and payoffs tracked and validated | Done (M1, M2), and in the final report (M8) |
| Evidence-based story feedback in the quality workflow | Done (M2, M8) |
| Coherent workspace with synchronized preview, timeline and inspector | Done (M3–M5) |
| Graphics and SFX are editable timeline items | Done (M4–M6) |
| Existing and new Remotion compositions render | Done (M5), verified on real renders |
| Preview and export consistent within documented limits | Done; checked per render by the final inspector (M8) |
| Automatic editing selective, story-aware, reversible | Done (M6, M7) |
| Creator edits and locks survive save/reopen and re-planning | Done (M4, M7) |
| Complete Short workflow on the packaged desktop app | **Not verified**: the installer wasn't built |
| Lyric Studio intact and regression-tested | Tests pass (69); no Lyric render was made |
| Tests, types, lint, builds, rendered-media checks reported | Done; full-repo lint has failures that pre-date the roadmap |
