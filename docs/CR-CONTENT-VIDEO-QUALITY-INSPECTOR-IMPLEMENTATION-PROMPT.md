# CR Content Studio — Video Quality Inspector Implementation Prompt

> **Target repository:** https://github.com/sokphaladam/cr-content  
> **Purpose:** Implement a professional, two-stage Video Quality Inspector for the existing Shorts Studio and Lyric Studio workflows.

Copy this document into Claude Code (or another coding agent) while working in the repository. The agent must inspect the real codebase before making changes. Do not assume file paths, frameworks, APIs, or architecture based only on this brief.

---

## 1. Role and objective

You are a senior desktop-video-product engineer, software architect, and QA engineer working inside the existing `cr-content` repository.

Improve CR Content Studio by adding a **Video Quality Inspector** that helps the creator assess production quality before uploading to YouTube.

The Inspector must have **two complementary stages**:

1. **Preview Inspector — before rendering:** analyzes the current editing project/timeline and provides fast feedback while the creator is editing.
2. **Final Render Inspector — after rendering:** analyzes the actual exported video file and verifies that the rendered result is technically correct and visually/audio-wise consistent with the intended output.

The Final Render Inspector is the authoritative check for the exported file. A successful Preview Inspector report must never be treated as proof that the final MP4 is correct.

The feature must support the two retained production workflows:

- **Shorts Studio:** vertical short-form videos, including the existing Shorts workflow and its specialized plan/import behavior.
- **Lyric Studio:** music lyric videos, including uploaded songs, lyric timing, visual backgrounds, animation, and existing rendering behavior.

Do not rebuild working video-generation or rendering engines just to add this feature. Integrate with the existing architecture after auditing it.

---

## 2. First: audit the existing repository

Before editing code:

1. Inspect the repository structure, README, package manifests, application entry points, and existing architecture documentation.
2. Identify the frontend framework, desktop runtime (if any), backend services, rendering engine, media-processing tools, storage layer, and test framework.
3. Trace the actual Shorts creation, preview, render, and export flows.
4. Trace the actual Lyric Studio song-upload, lyric synchronization, preview, render, and export flows.
5. Identify how timeline/project state, media assets, render jobs, output paths, and project IDs are represented and persisted.
6. Find existing media-analysis utilities, FFmpeg/FFprobe integrations, video players, waveform tools, subtitle components, and reusable report/status UI.
7. Inspect how the application currently handles progress, cancellation, errors, background tasks, and large files.
8. Identify platform constraints for Windows, macOS, and Linux, including where FFmpeg binaries are obtained and invoked.
9. Inspect existing tests and run the relevant baseline checks before modifying the code.

Produce a concise audit report with:

- Current architecture and actual rendering pipeline.
- Relevant existing files/modules and their responsibilities.
- Existing capabilities that can be reused.
- Missing capabilities.
- Risks and compatibility constraints.
- A file-by-file implementation plan.

**Do not guess names or create a parallel system if a suitable service already exists.** Adapt the plan to the repository discovered during the audit.

---

## 3. Product experience and user flow

The Inspector should be reachable from both Shorts Studio and Lyric Studio. It should feel like the final production stage, not a separate unrelated application.

Recommended user flow:

```text
Shorts Studio                         Lyric Studio
     |                                     |
     +----------- Edit / Preview ----------+
                       |
              Preview Inspector
                       |
            Resolve issues / continue
                       |
                    Render
                       |
              Final Render Inspector
                       |
          Resolve issues and re-render
                       |
             Final upload checklist
                       |
           Upload privately/unlisted
                       |
          Complete YouTube's own checks
```

### 3.1 Preview Inspector

The Preview Inspector runs against the **current editing project/timeline** before the final export.

It should provide two ways to inspect:

- **Quick checks:** inexpensive checks that can be run during editing or when opening the Inspector.
- **Full preview analysis:** a user-triggered analysis that samples relevant timeline sections, selected frames, audio segments, captions, and project metadata.

Do not continuously run expensive AI or frame analysis on every timeline change. Debounce lightweight checks and make expensive analysis explicit and cancellable.

### 3.2 Final Render Inspector

After a successful render, automatically offer to inspect the **actual output file**. Do not inspect only the project timeline or render settings.

The Inspector must:

- Confirm that the output file exists and is readable.
- Analyze the exported file's actual metadata, frames, and audio.
- Display a preview player for the exported file.
- Provide timestamped issues that can be clicked to seek the player to the relevant time.
- Allow the user to open the corresponding project/editor when a problem needs correction.
- Support re-rendering and re-inspecting.

Do not modify or overwrite the original rendered file during inspection.

---

## 4. Inspection profiles

Use one shared inspection engine with separate profiles for Shorts and lyric videos. Avoid duplicating all analyzer code.

### 4.1 Shorts profile

Prioritize:

- Correct vertical aspect ratio and target resolution.
- Strong opening visual and hook placement.
- Early delivery of the promised behavior or information.
- Visual relevance between narration and footage.
- Readability and safe placement of captions.
- Unwanted black/frozen frames and poor-quality footage.
- Narration/music balance and audio continuity.
- Repetitive shots or unnecessarily static sections.
- Ending/payoff and optional loop continuity.
- Title/thumbnail/publishing checklist, where project data exists.

Do not enforce one universal duration or a fixed cut frequency. Use the user's selected export profile and configurable project rules.

### 4.2 Lyric profile

Prioritize:

- Correct output aspect ratio and resolution.
- Song and video duration alignment.
- Missing, clipped, or prematurely ending audio.
- Lyric timing and synchronization with the song.
- Text readability, safe areas, contrast, and clipping.
- Long lines that exceed the canvas or become difficult to read.
- Visual movement that is too distracting or too subtle, when measurable.
- Frozen, black, or corrupted frames.
- Abrupt scene changes and unwanted visual gaps.
- Music/audio technical quality.
- Ending alignment and optional seamless-loop quality.

Where word-level lyric timing is unavailable, report that the check is limited rather than inventing a synchronization result.

---

## 5. Analysis categories and requirements

Every check must have a clear scope, result, severity, explanation, and evidence when applicable.

### 5.1 Technical video checks

Use FFprobe/FFmpeg or suitable existing media libraries to inspect the actual output file. Check:

- File exists, is non-empty, and can be decoded.
- Container format and video/audio stream presence.
- Actual width, height, aspect ratio, orientation, frame rate, duration, bitrate, codec, pixel format, and audio sample rate/channel layout.
- Unexpected mismatch between selected export profile and actual result.
- Unexpected duration or truncated output.
- Black frames or unintended black sections.
- Frozen/repeated frames beyond a configurable threshold.
- Decode errors or damaged streams.
- Unexpected borders/letterboxing where detectable.
- Audio/video duration mismatch and likely sync issues.
- Color-space metadata where available; flag unexpected or missing metadata for review rather than claiming a visual failure solely from metadata.

Use configurable export profiles. Sensible defaults may include 1080x1920 for Shorts and 1920x1080 for standard horizontal long videos, but do not hard-code these as the only valid outputs. Respect the creator's configured resolution, orientation, and frame rate.

Do not treat a frame-rate difference as automatically invalid if the project intentionally uses mixed source frame rates or a valid delivery conversion.

### 5.2 Visual quality checks

Implement deterministic checks where practical and use AI-assisted visual review only as an optional layer.

Potential checks:

- Blur/low sharpness in important frames.
- Severe underexposure or overexposure.
- Unusual color cast or major shot-to-shot color mismatch (as advisory signals).
- Main subject partially or fully outside the frame, where the subject can be identified reliably.
- Unwanted black borders or incorrect crop.
- Text/subtitles outside safe areas or clipped by canvas boundaries.
- Duplicate or near-duplicate shots.
- Long static sections or repeated frames.
- Abrupt visual gaps or missing media.
- Encoding artifacts, blockiness, or visible corruption.

Requirements:

- Sample frames intelligently across the timeline, including scene boundaries and user-selected important moments.
- Do not claim to have inspected every frame if only a sample was analyzed.
- Store a thumbnail/evidence frame for each actionable issue when possible.
- Avoid false certainty: some footage is intentionally soft, dark, grainy, slow, or static. Mark subjective judgments as warnings for human review.
- Never automatically change the creator's color grade or crop without approval.

### 5.3 Audio quality checks

Analyze the audio actually present in the timeline preview and final rendered file where possible.

Check:

- Missing audio stream.
- Unexpected silence or long gaps.
- Digital clipping and peak levels.
- Integrated loudness and loudness range where the tools support it.
- Sudden loudness changes.
- Narration versus music balance, when narration/music stems or reliable source tracks are available.
- Stereo channel imbalance, polarity/phase concerns, and mono compatibility where practical.
- Audio/video duration mismatch.
- Abrupt audio cuts or missing ending audio.

Do not impose a single universal loudness target. Provide configurable guidance for YouTube delivery and distinguish measured facts from recommendations.

If the final mix is a single audio track and the application does not have separate narration/music stems, do not pretend to know which component is too loud. Report measurable loudness/peaks and offer a human listening check.

### 5.4 Caption and lyric checks

Check:

- Text within the output canvas and configurable safe-area guides.
- Text clipping, overflow, and overlap with other text elements.
- Font size/readability using configurable heuristics.
- Low text/background contrast where measurable.
- Captions missing from expected timeline ranges, where caption data exists.
- Caption spelling using available transcript/text data.
- Caption timing and excessive rapid changes.
- Lyrics that appear too early/late relative to their timing data.
- Lyric lines extending beyond the song or video duration.
- Missing or duplicated lyric segments.

Do not modify original lyrics or captions automatically. Present suggested corrections for user approval.

### 5.5 Storytelling and retention-oriented review

This is an **editorial assistant**, not a viral-view predictor.

Use available script, narration transcript, scene/clip metadata, timeline structure, and selected visual samples to provide advisory checks such as:

**Shorts:**

- Is there an opening hook or immediate interesting visual?
- Does the opening establish a clear question, event, or promise?
- Does the video deliver an early payoff?
- Are there sections with no clear narrative purpose?
- Does the narration correspond to the footage?
- Is there a clear sequence: hook, development, payoff?
- Does the ending feel complete, abrupt, or intentionally loopable?

**Long-form, if supported by an existing retained workflow:**

- Does the opening establish the main promise?
- Is the introduction disproportionately long compared with the story?
- Are there repetitive explanations or scenes?
- Are major claims supported by relevant visuals?
- Are there long sections without meaningful new information or visual development?
- Does the conclusion address the central question?

**Lyric videos:**

- Does the visual treatment fit the song's mood?
- Are lyric changes aligned with musical sections?
- Are visuals or text animations excessively distracting?
- Does the video have an intentional visual progression?
- Is the ending aligned with the musical ending?

Use language such as "consider reviewing" or "possible pacing issue." Never state that a particular edit will guarantee retention, views, or virality.

### 5.6 Rights and publishing checklist

Provide a user-editable asset-rights checklist with fields such as:

- Asset name and type (footage, image, music, sound effect, voice, font, etc.).
- Original source/creator.
- License or permission reference.
- Attribution required and attribution text.
- Commercial-use permission status.
- Modification/derivative-use permission status.
- Expiration or other restrictions, if applicable.
- User confirmation and notes.

Clearly distinguish:

- **Locally documented:** the user entered a source/license record.
- **Not verified:** the application has not independently verified the legal status.
- **Requires YouTube check:** Content ID, copyright, ad suitability, and platform-specific checks must be completed in YouTube Studio.

Do not claim local analysis can replace YouTube Content ID or official monetization checks.

---

## 6. Issue model and status semantics

Use consistent issue/report data structures across preview and final-render inspections.

Each issue should support fields equivalent to:

```ts
type QualityIssue = {
  id: string;
  stage: "preview" | "render";
  category:
    | "technical"
    | "visual"
    | "audio"
    | "captions"
    | "lyrics"
    | "storytelling"
    | "rights";
  severity: "critical" | "high" | "medium" | "low" | "info";
  status: "fail" | "warning" | "pass" | "not_checked";
  title: string;
  description: string;
  recommendation?: string;
  timestampStart?: number;
  timestampEnd?: number;
  evidenceImagePath?: string;
  detectorId: string;
  confidence?: number;
  canAutoFix?: boolean;
  suggestedAction?: string;
  userDisposition?: "unreviewed" | "accepted" | "dismissed" | "fixed";
};
```

Adapt this example to the repository's language and conventions rather than copying it blindly.

Report statuses:

- **PASS:** the check ran and met its configured criteria.
- **WARNING:** the check found a potential issue or needs human review.
- **FAIL:** a required technical check failed or a configured blocking rule was violated.
- **NOT CHECKED:** the check could not run, is unsupported, or was skipped.

Do not silently treat `NOT CHECKED` as `PASS`.

Avoid a single misleading "quality score" that hides critical failures. If an overall summary is included, show category results and blocking issues alongside it. Explain how any numerical score is calculated and never imply it predicts views.

---

## 7. User interface requirements

Build a professional inspection workspace consistent with the existing CR Content Studio design system.

### 7.1 Inspector layout

Recommended layout:

- Header with project name, output filename, profile, inspection stage, and inspection date.
- Large video preview player.
- Timeline with issue markers and category filters.
- Quality summary grouped by category.
- Timestamped issue list.
- Evidence frame and suggested fix for the selected issue.
- Controls to run/re-run inspection, cancel, and open the relevant editor.
- Final status and upload-readiness checklist.

### 7.2 Issue interaction

When the user selects an issue:

1. Seek the preview player to `timestampStart`.
2. Show the evidence frame if available.
3. Highlight the corresponding timeline marker/region.
4. Explain what was detected and why it matters.
5. Provide an appropriate action, such as opening the editor at the relevant section, replacing a source clip, adjusting a caption, or reviewing audio.

Use stable IDs so issues do not unexpectedly change identity when a report is refreshed.

### 7.3 Fix suggestions and automation

- Prefer actionable suggestions over vague judgments.
- Only offer an automatic fix when the application can perform it reliably and safely.
- Preview any automatic change before applying it.
- Require user approval before modifying the project/timeline.
- Never alter the final exported file in place.
- After a fix, mark the old issue as fixed only when a new inspection confirms that it is resolved.

### 7.4 Progress and cancellation

- Show progress by analysis stage/category.
- Allow cancellation of long-running inspections.
- Do not freeze the editor UI while analyzing media.
- Handle missing tools, unsupported codecs, permission errors, out-of-space errors, and corrupted files gracefully.
- Preserve partial reports when an inspection is cancelled or partially fails, and clearly identify what was not checked.

---

## 8. Technical architecture guidance

Create a shared Quality Inspector service integrated with the existing application architecture.

Potential logical modules (adapt names and locations to the actual repository):

```text
QualityInspector/
  Shared/
    InspectionOrchestrator
    QualityRules
    IssueNormalizer
    ReportStore
    MediaFingerprint
    ProfileRegistry

  Preview/
    TimelineAnalyzer
    SceneSampler
    PreviewAudioAnalyzer
    CaptionAnalyzer
    StoryAnalyzer

  Render/
    FileValidator
    MediaMetadataAnalyzer
    FrameAnalyzer
    RenderAudioAnalyzer
    ExportValidator

  Detectors/
    BlackFrameDetector
    FreezeDetector
    BlurDetector
    ExposureDetector
    SilenceDetector
    ClippingDetector
    AspectRatioDetector
    SubtitleBoundsDetector
    DuplicateShotDetector

  Profiles/
    ShortsProfile
    LyricProfile

  UI/
    InspectorWorkspace
    VideoPreview
    IssueTimeline
    QualitySummary
    IssueDetails
    RightsChecklist
```

### 8.1 Suggested tools

Reuse existing tools first. If the repository does not already have suitable equivalents, evaluate:

- **FFprobe:** actual media metadata and stream inspection.
- **FFmpeg:** decoding, frame sampling, black/freeze detection, audio filters, and media analysis.
- **OpenCV:** frame-level blur, exposure, image comparison, and crop-related heuristics.
- **Existing player component:** final-output playback and timestamp seeking.
- **Existing waveform/audio tooling:** waveform display and audio review.
- **Optional AI vision model:** selected-frame review for subjective visual composition and anomalies.
- **Optional speech-to-text:** transcript generation when no script or narration text exists.
- **Optional AI text/vision model:** editorial review using script/transcript and sampled frames.

Do not add a new heavy dependency without explaining why it is required. Pin or constrain dependency versions consistently with the project.

### 8.2 Local-first baseline

All essential technical validation should work locally without an AI API key or paid token usage.

AI features must be optional, separately configurable, and clearly labeled. If AI is unavailable, the deterministic checks and manual review workflow must still work.

Do not upload private project media to external AI services without explicit user configuration and consent. Provide a clear explanation of what data would be sent.

### 8.3 Performance

- Avoid decoding every frame for every quick preview check.
- Use configurable frame sampling and targeted analysis around scene boundaries or suspicious regions.
- Use proxies or low-resolution samples for quick preview checks where appropriate.
- Use deeper analysis on the rendered output when the user runs Final Render Inspection.
- Cache reusable analysis results safely.
- Run jobs outside the UI thread/process where appropriate.
- Support progress reporting, cancellation, and bounded concurrency.
- Avoid retaining large temporary files indefinitely.

### 8.4 Report persistence and file identity

Associate reports with the project ID, inspection profile, stage, output path (when applicable), and media fingerprint.

For final rendered files:

- Calculate a stable file fingerprint (prefer a cryptographic hash where practical).
- Record file size and modification metadata as supplemental data.
- If the output file changes, mark the previous render report as **outdated**.
- Do not reuse a previous report for a different file merely because the filename is unchanged.

For preview reports:

- Associate the report with the project/timeline revision or a reliable project-state fingerprint.
- Mark the report outdated when relevant timeline state changes.

Store reports using the existing persistence conventions. Do not introduce a second database or storage format without a demonstrated need.

---

## 9. APIs and contracts

Audit existing IPC/API conventions first. Reuse them where possible. Define clear contracts for:

- Start preview inspection.
- Start final render inspection.
- Get inspection progress/status.
- Cancel an inspection.
- Retrieve report and issues.
- Mark an issue reviewed/dismissed/fixed.
- Open an issue timestamp in the player/editor.
- Re-run inspection.
- Get or update profile rules.
- Manage asset-rights checklist records.

Every operation should validate input, handle missing files, and return typed errors. Avoid exposing arbitrary filesystem access through renderer/UI inputs. Validate file paths and project ownership at the trusted process/service boundary.

The UI should never claim an inspection passed until the analyzer has actually completed the corresponding checks.

---

## 10. Rules for automated correction

The first implementation should focus on **detection and guidance**, not automatic editing.

Possible future automatic fixes, only when supported by the existing editor:

- Move a caption inside safe margins.
- Reduce a music track's gain by a user-selected amount.
- Replace a missing media reference after the user chooses a replacement.
- Adjust an export profile to match the user's chosen format.

Requirements:

- Never change the original source media.
- Never overwrite the final MP4 during inspection.
- Show a before/after preview where possible.
- Ask for confirmation before applying changes.
- Preserve undo/redo behavior.
- Re-render after project changes, then re-run final inspection.

Do not automatically rewrite a script, change factual narration, change a lyric, recolor footage, or recrop a subject without user approval.

---

## 11. Testing strategy

Create automated tests for detectors and integration tests for the complete workflow.

### 11.1 Test media fixtures

Generate or add legally usable small test fixtures with known expected properties:

- Valid vertical Short.
- Valid horizontal video.
- Video with no audio stream.
- Video with a black section.
- Video with a frozen section.
- Video with silence.
- Video with clipped audio.
- Unexpected resolution/aspect ratio.
- Truncated or corrupt file.
- Video with an intentionally clipped caption (if test rendering supports it).
- Lyric video with correctly synchronized lyrics.
- Lyric video with deliberately offset lyric timing.

Keep fixtures small enough for CI and document how they were created.

### 11.2 Required tests

- Each detector returns the expected result for positive and negative fixtures.
- A failed or unsupported detector returns `NOT CHECKED` or a clear error, never a false `PASS`.
- Preview and render reports use the correct profile.
- Clicking an issue seeks to the correct timestamp.
- Re-rendering changes the file fingerprint and invalidates the prior report.
- Timeline edits invalidate relevant preview results.
- Cancelled inspection is reported accurately.
- Missing FFmpeg/FFprobe or invalid binaries produce actionable errors.
- Existing Shorts rendering continues to work.
- Existing lyric rendering and synchronization continue to work.
- Existing project/library data remains readable.

### 11.3 Regression checks

Run the repository's relevant:

- Type checking.
- Linting.
- Unit tests.
- Integration tests.
- Frontend production build.
- Backend tests.
- Desktop packaging/build checks, if supported.

Do not claim tests passed unless they were actually executed. Report skipped tests and environmental limitations.

---

## 12. Implementation milestones

Implement incrementally. Keep the app usable at the end of each milestone.

### Milestone 1 — Architecture and technical final-render inspection

- Complete repository audit.
- Define shared issue/report types and profile contracts.
- Integrate actual output-file inspection after rendering.
- Implement FFprobe/FFmpeg file integrity, metadata, duration, black-frame, freeze, missing-audio, silence, and basic sync checks.
- Build a basic report UI.
- Add a final-output preview player with timestamp navigation.

**Acceptance:** A user can render a Short or lyric video, inspect the actual exported file, view technical results, and jump to timestamped issues.

### Milestone 2 — Preview Inspector

- Analyze current timeline/project state.
- Add quick checks and a user-triggered full preview analysis.
- Check project dimensions, media references, timing, caption bounds, audio tracks, and basic scene structure.
- Mark preview reports outdated after relevant timeline edits.

**Acceptance:** The user can find common editing mistakes before rendering, and the UI clearly distinguishes preview analysis from final rendered-file verification.

### Milestone 3 — Visual and audio quality analysis

- Add OpenCV or existing-library detectors for blur, exposure, crop/border, and duplicate/repeated shots where reliable.
- Improve audio loudness, clipping, silence, and channel checks.
- Add evidence frames and actionable suggestions.

**Acceptance:** Visual/audio problems are reported with timestamps and evidence, with subjective findings labeled as warnings.

### Milestone 4 — Shorts and Lyric profiles; editorial assistance

- Add separate profile rules for Shorts and Lyric Studio.
- Add caption and lyric synchronization checks.
- Add optional story/pacing review using available scripts, transcripts, timeline metadata, and sampled visuals.
- Add the asset-rights and publishing checklist.

**Acceptance:** The two workflows receive relevant checks without duplicated engines or irrelevant warnings.

### Milestone 5 — Performance, persistence, polish, and regression

- Add report history and file/project fingerprint invalidation.
- Improve progress, cancellation, recovery, and large-file handling.
- Add all fixture-based tests and regression checks.
- Update README and user documentation.
- Verify packaging on the supported operating systems.

**Acceptance:** The Inspector is reliable, understandable, reusable, and does not regress existing Shorts or Lyric Studio production.

---

## 13. Definition of done

The feature is complete only when all of the following are true:

- [ ] Both Shorts Studio and Lyric Studio can open the Preview Inspector.
- [ ] Both workflows can inspect their actual final rendered output.
- [ ] Preview and final-render results are visibly distinguished.
- [ ] Final-render inspection reads the exported file, not only the project timeline.
- [ ] Reports show category, status, severity, description, and timestamps where applicable.
- [ ] Selecting an issue seeks to the right timestamp in the relevant player.
- [ ] Evidence frames are shown where available.
- [ ] `NOT CHECKED` is never silently treated as `PASS`.
- [ ] Preview reports are invalidated when relevant project/timeline state changes.
- [ ] Render reports are invalidated when the output file changes.
- [ ] Baseline technical checks run locally without AI tokens.
- [ ] AI-based reviews are optional and never claim to predict views or guarantee retention.
- [ ] Rights documentation is clearly separated from actual YouTube copyright verification.
- [ ] Existing Shorts and lyric creation/rendering behavior still works.
- [ ] Existing user projects and output files are preserved.
- [ ] Automated tests cover known-good and known-bad media fixtures.
- [ ] Documentation explains supported checks, limitations, and how to interpret reports.

---

## 14. Required final response from the coding agent

When implementation work is complete, provide:

1. Repository architecture findings.
2. Milestones completed and not completed.
3. Files added, modified, and removed.
4. Exact checks implemented for Preview Inspector and Final Render Inspector.
5. Which checks are deterministic, heuristic, or AI-assisted.
6. New dependencies and why they were needed.
7. API/IPC contracts introduced or modified.
8. Test commands executed and their real results.
9. Known limitations, false-positive risks, and unsupported checks.
10. Manual steps needed to test the feature in Shorts Studio and Lyric Studio.

If the work is too large for one pass, complete the current milestone cleanly, leave the project buildable, document remaining work, and stop. Do not silently skip requirements or claim completion without evidence.

---

## 15. Start here

Begin by auditing the existing repository and reporting the actual implementation plan. Then implement **Milestone 1 only** unless the repository's current state makes a smaller preparatory change necessary.

Preserve working features. Prefer focused, testable changes over a large rewrite.
