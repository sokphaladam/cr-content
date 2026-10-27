# Graph Report - cr-content  (2026-10-28)

## Corpus Check
- 250 files · ~285,794 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 6, .woff2 3, .example 2)

## Summary
- 3938 nodes · 10787 edges · 151 communities (138 shown, 13 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 284 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Core Web API
- Campaign UI
- Folder & Path Settings
- Footage & Clip Picking
- Neon Mekong Core
- Addons & Install
- Longform Settings
- Drafts & Art Status
- Archives & Fetching
- Settings & Keys UI
- Create Form
- Tauri Desktop Shell
- Live Caption Preview
- Lyrics Alignment
- Longform Extras & Credits
- Lyrics Timing UI
- Studio Page
- Highlights Card
- Lyric Video Builder
- Visual FX & Depth
- Cover Frames
- Song Generation
- Music Finder
- Neon Lyric Scenes
- Make-Song CLI
- Caption & Music Video Options
- Beats & Pipeline Art
- Campaign Backend
- Scheduling
- Analytics
- Longform Storyboard
- Campaign Upload & Footage
- Docs & READMEs
- Campaign Clips & Highlights API
- Library UI
- Script & Scene Model
- Edit & Grade Filters
- Longform Timing
- LRC & Hook Planning
- Caption ASS Rendering
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 150

## God Nodes (most connected - your core abstractions)
1. `Button()` - 88 edges
2. `post()` - 79 edges
3. `Script` - 63 edges
4. `SongScript` - 55 edges
5. `duration()` - 54 edges
6. `Word` - 54 edges
7. `make_client()` - 53 edges
8. `make_video()` - 51 edges
9. `make_music_video()` - 47 edges
10. `Timeline` - 45 edges

## Surprising Connections (you probably didn't know these)
- `The Smartest Birds on Earth, Ranked - Video Script` --semantically_similar_to--> `Pasted script: 3 Octopus Facts That Sound Fake`  [INFERRED] [semantically similar]
  scripts/smartest-birds.md → examples/pasted-octopus.txt
- `text()` --indirect_call--> `font()`  [INFERRED]
  crcontent/fx.py → neonmekong/thumbnail.py
- `search()` --indirect_call--> `item()`  [INFERRED]
  crcontent/longform/footage.py → tests/test_packaging.py
- `test_a_card_for_a_graphic_scene_is_not_flagged_but_a_fallback_card_is()` --calls--> `flags()`  [EXTRACTED]
  tests/test_longform_footage.py → crcontent/longform/footage.py
- `job()` --uses--> `Slot`  [INFERRED]
  tests/test_longform_own_file.py → crcontent/longform/timing.py

## Import Cycles
- 3-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/preflight.py -> crcontent/shorts/edit.py -> crcontent/shorts/__init__.py`
- 3-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/preflight.py -> crcontent/shorts/graphics.py -> crcontent/shorts/__init__.py`
- 3-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/preflight.py -> crcontent/shorts/judge.py -> crcontent/shorts/__init__.py`
- 3-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/render.py -> crcontent/shorts/edit.py -> crcontent/shorts/__init__.py`
- 4-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/preflight.py -> crcontent/shorts/edit.py -> crcontent/shorts/graphics.py -> crcontent/shorts/__init__.py`
- 4-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/render.py -> crcontent/shorts/captions.py -> crcontent/shorts/graphics.py -> crcontent/shorts/__init__.py`
- 4-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/render.py -> crcontent/shorts/edit.py -> crcontent/shorts/graphics.py -> crcontent/shorts/__init__.py`
- 5-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/preflight.py -> crcontent/shorts/edit.py -> crcontent/shorts/captions.py -> crcontent/shorts/graphics.py -> crcontent/shorts/__init__.py`
- 5-file cycle: `crcontent/shorts/__init__.py -> crcontent/shorts/render.py -> crcontent/shorts/edit.py -> crcontent/shorts/captions.py -> crcontent/shorts/graphics.py -> crcontent/shorts/__init__.py`

## Hyperedges (group relationships)
- **Script input formats consumed by the generator** — scripts_smartest_birds, examples_pasted_octopus, readme_excel_plan [INFERRED 0.75]
- **Neon Mekong song inputs** — neonmekong_readme_suno_txt, tests_fixtures_songs_demo_song_suno, neonmekong_readme_song_json [INFERRED 0.75]

## Communities (151 total, 13 thin omitted)

### Community 0 - "Core Web API"
Cohesion: 0.04
Nodes (61): frame_size(), elevenlabs_key(), caption_catalog(), art_download(), art_draw(), ArtDrawRequest, ArtPlanEdit, ArtPlanSlotEdit (+53 more)

### Community 1 - "Campaign UI"
Cohesion: 0.04
Nodes (74): CampaignDetail(), ClipCard(), fromLines(), fromWords(), listText(), MakeClips(), Panel(), PLATFORM_LABEL (+66 more)

### Community 2 - "Folder & Path Settings"
Cohesion: 0.06
Nodes (37): folder(), aspect(), _box(), _dissolve(), encoder(), _fonts(), join(), music_bed() (+29 more)

### Community 3 - "Footage & Clip Picking"
Cohesion: 0.04
Nodes (35): clip_start(), name_animal(), own_pick(), placeholders(), sources(), tagged(), weak(), capped() (+27 more)

### Community 4 - "Neon Mekong Core"
Cohesion: 0.05
Nodes (29): _arrays(), ImageChops_offset(), norm(), text_sprite(), wrap(), intro_span(), neon_gain(), neon_name() (+21 more)

### Community 5 - "Addons & Install"
Cohesion: 0.07
Nodes (32): activate(), _fetch(), frozen(), install(), _install(), _install_packages(), on_line(), show() (+24 more)

### Community 6 - "Longform Settings"
Cohesion: 0.07
Nodes (30): load(), _merge(), apply_change(), is_short(), _load(), make_job(), _make_steps(), media_folder() (+22 more)

### Community 7 - "Drafts & Art Status"
Cohesion: 0.05
Nodes (42): list_drafts(), load_art_plan(), art_progress(), events(), art_status(), ArtPlanSongRequest, direct_video_idea(), DirectionEdit (+34 more)

### Community 8 - "Archives & Fetching"
Cohesion: 0.05
Nodes (34): archive(), _archive_clip(), black_bars(), fetch(), _get(), inaturalist(), met(), nasa() (+26 more)

### Community 9 - "Settings & Keys UI"
Cohesion: 0.06
Nodes (54): Campaigns(), NewCampaign(), AppearanceRows(), AppKeysForm(), save(), BackgroundRow(), ChannelRow(), CleanUp() (+46 more)

### Community 10 - "Create Form"
Cohesion: 0.07
Nodes (38): CreateForm(), LongVideoForm(), LYRICS_EXAMPLE, Mode, OwnSongForm(), PASTE_EXAMPLE, PLACEHOLDER, ExcelPlanForm() (+30 more)

### Community 11 - "Tauri Desktop Shell"
Cohesion: 0.06
Nodes (27): app_version(), autostart_enabled(), AUTOSTART_LABEL, AutostartItem, BACKGROUND_ARG, build_tray(), check_update(), Engine (+19 more)

### Community 12 - "Live Caption Preview"
Cohesion: 0.07
Nodes (52): captionAt(), cased(), cq(), Draggable(), fontOf(), Footage(), FrameEdits, LANG_CAPTION (+44 more)

### Community 13 - "Lyrics Alignment"
Cohesion: 0.08
Nodes (31): _align(), align_lyrics(), _cut(), even_timing(), _fill_gaps(), _flag(), _forced_timing(), refine() (+23 more)

### Community 14 - "Longform Extras & Credits"
Cohesion: 0.07
Nodes (34): _attributions(), credits(), description(), thumbnail_text(), write(), _cells(), chapters_from(), clock() (+26 more)

### Community 15 - "Lyrics Timing UI"
Cohesion: 0.09
Nodes (42): Caption(), LyricMonitor(), Kbd(), LyricsTiming(), Save, SHORTCUTS, SPEEDS, TimeInput() (+34 more)

### Community 16 - "Studio Page"
Cohesion: 0.08
Nodes (44): Page(), Studio(), deleteVideo(), duplicateDraft(), openTiming(), selectDraft(), selectVideo(), startNew() (+36 more)

### Community 17 - "Highlights Card"
Cohesion: 0.06
Nodes (38): clock(), HighlightsCard(), Pick(), savedArtist(), STEPS, PackagingReview(), Score(), ExportCards() (+30 more)

### Community 18 - "Lyric Video Builder"
Cohesion: 0.09
Nodes (30): _audio(), bind(), _clear_background(), create_song(), delete_song(), _detail(), draw_status(), edit_song() (+22 more)

### Community 19 - "Visual FX & Depth"
Cohesion: 0.06
Nodes (18): available(), _blur(), _camera(), depth_map(), _device(), _ease(), _LightLeak, _LightTrails (+10 more)

### Community 20 - "Cover Frames"
Cohesion: 0.08
Nodes (24): _accent(), best_frames(), _frame_image(), _lines(), make_covers(), _mixed_sprite(), render_cover(), score_frame() (+16 more)

### Community 21 - "Song Generation"
Cohesion: 0.08
Nodes (24): Client, make_client(), describe_song(), fit_length(), generate_song(), _header_name(), idea_queries(), move_notes() (+16 more)

### Community 22 - "Music Finder"
Cohesion: 0.08
Nodes (42): length(), MusicFinder(), PictureReview(), emptyScene(), FactCheck(), groupVoices(), LEFT_TABS, LeftTab (+34 more)

### Community 23 - "Neon Lyric Scenes"
Cohesion: 0.08
Nodes (22): active_line(), build_scene(), card_alpha(), crisp(), ease(), encode(), lyric_y(), move_clip() (+14 more)

### Community 24 - "Make-Song CLI"
Cohesion: 0.09
Nodes (31): cmd_all(), cmd_analyze(), cmd_checklist(), cmd_hook(), cmd_init(), cmd_instrumental(), cmd_schedule(), cmd_short() (+23 more)

### Community 25 - "Caption & Music Video Options"
Cohesion: 0.07
Nodes (39): CaptionPanel(), Mode, fontFor(), fromPreset(), LOOK_CSS, LyricPreview(), MUDDY_ON_COVER, MusicVideoOptions() (+31 more)

### Community 26 - "Beats & Pipeline Art"
Cohesion: 0.09
Nodes (23): beat_times(), _cover_subject(), _design_about(), draw_designed(), draw_thumbnail(), _existing(), import_song(), job_size() (+15 more)

### Community 27 - "Campaign Backend"
Cohesion: 0.12
Nodes (30): add_file(), Campaign, _claude(), ClipPlan, delete(), _dir(), _download(), _fit() (+22 more)

### Community 28 - "Scheduling"
Cohesion: 0.08
Nodes (30): clips(), add(), cancel(), forget_video(), goes_early(), items(), _load(), mark() (+22 more)

### Community 29 - "Analytics"
Cohesion: 0.07
Nodes (23): _avg(), _column(), import_csv(), length_bucket(), load(), match(), _NoAI, _num() (+15 more)

### Community 30 - "Longform Storyboard"
Cohesion: 0.10
Nodes (21): _index(), _load(), make_storyboard(), media_folder(), pick_footage(), reload_media(), render_video(), _save() (+13 more)

### Community 31 - "Campaign Upload & Footage"
Cohesion: 0.08
Nodes (26): campaign_prepare(), campaign_upload(), excel_read(), FootagePick, FootageSearch, import_own_song(), _longform_busy(), _longform_dir() (+18 more)

### Community 32 - "Docs & READMEs"
Cohesion: 0.05
Nodes (42): Pasted script: 3 Octopus Facts That Sound Fake, Octopus facts (3 hearts, blue blood, arms that think), Chat-assistant script format ([0-3s] Hook, Visual, On-screen text, Voiceover), Frontend README (create-next-app template), Next.js, Neon Mekong song pipeline README, Upload text and AI (template, Ollama local, Gemini), Hook-first edits (trim / chorus preview) (+34 more)

### Community 33 - "Campaign Clips & Highlights API"
Cohesion: 0.10
Nodes (30): _auto_publish(), campaign_clips(), ClipRequest, _fail(), find_highlights(), HighlightsRequest, _job_logger(), log() (+22 more)

### Community 34 - "Library UI"
Cohesion: 0.08
Nodes (32): dateGroup(), Filter, FILTER_LABEL, Item, ItemType, Library(), Row(), RowMenu() (+24 more)

### Community 35 - "Script & Scene Model"
Cohesion: 0.09
Nodes (19): Scene, Script, trim_window(), ShortPlan, job(), csv_file(), _ep(), offline() (+11 more)

### Community 36 - "Edit & Grade Filters"
Cohesion: 0.09
Nodes (26): Slot, cut_filter(), grade(), graphics_names(), _hits(), load(), options(), preview() (+18 more)

### Community 37 - "Longform Timing"
Cohesion: 0.13
Nodes (21): Chapter, build(), _scene_for(), Timeline, Voice, checks(), cut_suggestion(), spoken_end() (+13 more)

### Community 38 - "LRC & Hook Planning"
Cohesion: 0.10
Nodes (23): parse_lrc(), _ffmpeg(), plan(), render_audio(), run(), shifted(), snap_back(), Variant (+15 more)

### Community 39 - "Caption ASS Rendering"
Cohesion: 0.11
Nodes (19): _balance(), build_ass(), _case(), _circle(), _esc(), _hook_events(), now_playing_events(), disc() (+11 more)

### Community 40 - "Community 40"
Cohesion: 0.08
Nodes (22): text(), cut(), ease_out_back(), fill_fraction(), Grader, _hits(), pick(), pop_scale() (+14 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (21): audio_features(), energy_between(), fill(), find_audio(), lrc(), _mean(), measure(), mock() (+13 more)

### Community 42 - "Community 42"
Cohesion: 0.09
Nodes (17): _ask(), check_picture(), clean_section(), _client(), direct_idea(), find_subject(), plan_scenes(), plan_song() (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.10
Nodes (19): auto_emphasis(), _bare(), build_thumbnail_ass(), edge(), fit(), ink(), step(), width() (+11 more)

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (20): edit_pictures(), _pictures(), reset_pictures(), suggest_motions(), ai_prompts(), load(), _lyrics_between(), path() (+12 more)

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (16): _ask(), background(), clean_svg(), _client(), _cover_fonts(), design_cover(), _font_dirs(), _jpeg_block() (+8 more)

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (17): pinned_comment(), sources_line(), Episode, episode_lang(), _get(), _key_scene(), music_tracks(), _norm() (+9 more)

### Community 47 - "Community 47"
Cohesion: 0.14
Nodes (18): karaoke_font(), _add_hook(), _ass_text(), encoder(), lyric_box(), place_hook(), render(), _shift() (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (15): focus_sharpness(), has_camera_move(), judged(), motion(), _reject(), Sample, _samples(), Scan (+7 more)

### Community 49 - "Community 49"
Cohesion: 0.12
Nodes (25): AddonProgress(), artBlocker(), ArtStylePicker(), DownloadProgress(), eta(), gb(), mbps(), MOTION_ORDER (+17 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (17): run(), backup(), from_suno(), genre_of(), move_aside(), save(), slugify(), warnings() (+9 more)

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (18): _cover_photo(), _download(), download_stock(), _get(), is_image(), _pexels(), _pexels_best_file(), _pexels_download() (+10 more)

### Community 52 - "Community 52"
Cohesion: 0.16
Nodes (26): addScene(), api(), esc(), fillVoices(), fmtDate(), listen(), loadLibrary(), loadOptions() (+18 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (10): Animation, _bezier(), _clock(), _fmt(), _lerp(), _local(), Player, _render_frame() (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (9): _wait_seconds(), Response, ElevenLabsError, ElevenLabsMusic, get_backend(), _song_id(), SongBackend, SongResult (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.16
Nodes (25): AboutRows(), mb(), UpdateNotice(), AppUpdate, appVersion(), checkUpdate(), desktop(), installUpdate() (+17 more)

### Community 56 - "Community 56"
Cohesion: 0.07
Nodes (27): app, security, windows, cwd, script, cwd, script, build (+19 more)

### Community 57 - "Community 57"
Cohesion: 0.11
Nodes (12): overlay_lines(), ass_color(), available_fonts(), CaptionStyle, catalog(), font_dirs(), font_path(), _hex() (+4 more)

### Community 58 - "Community 58"
Cohesion: 0.11
Nodes (13): _keywords(), _clean(), cuts(), impacts(), sound_times(), _fallback_query(), norm_title(), _ask() (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.14
Nodes (14): APIConnectionError, APIError, APIStatusError, AuthenticationError, BadRequestError, _Beta, Block, build_body() (+6 more)

### Community 60 - "Community 60"
Cohesion: 0.08
Nodes (19): _verdict(), art_check(), art_plan(), ArtCheckRequest, ArtPlanRequest, campaign_create(), CampaignReadRequest, ideas() (+11 more)

### Community 61 - "Community 61"
Cohesion: 0.08
Nodes (25): activation_command, activation_command_timeout, added_modes, agent_interface, default_modes, encoding, excluded_apis, excluded_tools (+17 more)

### Community 62 - "Community 62"
Cohesion: 0.16
Nodes (17): create(), delete(), Draft, _folder(), import_rendered_videos(), load(), _now(), save() (+9 more)

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (14): find_outliers(), fluff_opening(), _opening(), OutlierError, _post(), review(), _seconds(), set_journey() (+6 more)

### Community 64 - "Community 64"
Cohesion: 0.11
Nodes (9): main(), stdlib_extensions(), client(), _run(), test_analyze_dry_run(), test_user_edits_survive_and_backup_kept(), _song(), test_bad_palette_falls_back() (+1 more)

### Community 65 - "Community 65"
Cohesion: 0.10
Nodes (13): _call_gemini(), generate(), parse_reply(), prompt(), dry_run(), set_dry_run(), FakeResponse, song() (+5 more)

### Community 66 - "Community 66"
Cohesion: 0.14
Nodes (11): spans_from_lines(), _allin1(), analyze(), _bars(), _guess_sections(), kind(), _norm(), _per_second() (+3 more)

### Community 67 - "Community 67"
Cohesion: 0.13
Nodes (14): _cached(), _commons(), _pexels(), _pexels_file(), _pixabay(), _pixabay_file(), rank(), research() (+6 more)

### Community 68 - "Community 68"
Cohesion: 0.14
Nodes (15): _app_key(), _creds(), disconnect(), _finish_connect(), _finish_meta(), _import_env_keys(), _load(), _save() (+7 more)

### Community 69 - "Community 69"
Cohesion: 0.13
Nodes (5): choose(), fetch_preview(), _finish(), full(), Picker

### Community 70 - "Community 70"
Cohesion: 0.15
Nodes (11): Candidate, candidates(), _earliest(), _latest(), _mean(), _overlap(), pick(), adjusted() (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.17
Nodes (12): _app_home(), check(), current(), _default_data(), documents(), first_run(), _inside(), _move() (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.13
Nodes (9): credit(), download(), _plain(), search(), real_subject_media(), _Response, _setup(), test_a_429_asking_for_a_long_wait_fails_fast() (+1 more)

### Community 73 - "Community 73"
Cohesion: 0.10
Nodes (11): orientation(), _clock(), _hex_brightness(), make_music_video(), neon_title(), plan_fits(), plan_follows(), report() (+3 more)

### Community 74 - "Community 74"
Cohesion: 0.16
Nodes (12): download(), downloaded(), _expected_bytes(), gpu_name(), installed(), _live_progress(), _model_dir(), _patterns() (+4 more)

### Community 75 - "Community 75"
Cohesion: 0.19
Nodes (11): collect(), _files(), _prune(), _references(), run(), scan(), _size(), _file() (+3 more)

### Community 76 - "Community 76"
Cohesion: 0.16
Nodes (12): _caption(), clean_tags(), comment_text(), _is_short(), _own_comment(), post_text(), _send_thumbnail(), set_youtube_options() (+4 more)

### Community 77 - "Community 77"
Cohesion: 0.15
Nodes (9): apply_cuts(), _merged(), peaks(), scene_voice(), spoken(), transcript(), voice_key(), with_emoji() (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.17
Nodes (10): _clean(), detect_lang(), import_script(), import_with_claude(), parse_basic(), strip_emoji(), BRoll, Scene (+2 more)

### Community 79 - "Community 79"
Cohesion: 0.18
Nodes (9): make_highlights(), _alike(), analyze(), letters(), LyricScores, score(), _words(), load() (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.16
Nodes (11): _background(), cover_canvas(), _crisp(), _drop_strays(), _flatten(), picture_shape(), scene_cover(), test_a_scene_is_kept_whole() (+3 more)

### Community 81 - "Community 81"
Cohesion: 0.18
Nodes (14): draw_magazine(), bounds(), cols_in(), hidden(), legible(), line(), panel(), panel_lines() (+6 more)

### Community 82 - "Community 82"
Cohesion: 0.16
Nodes (6): clip_key(), Registry, Use, uses(), _short(), test_registry_rules()

### Community 83 - "Community 83"
Cohesion: 0.17
Nodes (8): basic_headlines(), best_frames(), brief(), _frame_jpeg(), _frame_score(), opening_score(), plan_covers(), suggestions()

### Community 84 - "Community 84"
Cohesion: 0.15
Nodes (18): devDependencies, concurrently@^10.0.5, tailwindcss@^4, @tailwindcss/postcss@^4, @types/node@^20, @types/react@^19, @types/react-dom@^19, typescript@^5 (+10 more)

### Community 85 - "Community 85"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 86 - "Community 86"
Cohesion: 0.17
Nodes (8): _build_fonts(), _download(), emojify_ass(), _glyph(), _layers(), _load(), _rewrite(), strip()

### Community 87 - "Community 87"
Cohesion: 0.12
Nodes (9): default_effects(), art_ready(), make_video(), wrong(), picture_check_on(), plan_scene_art(), release_gpu(), FootagePicker (+1 more)

### Community 88 - "Community 88"
Cohesion: 0.20
Nodes (9): check(), flags(), make_card(), montage(), own_media(), reload_own(), _size(), _thumb() (+1 more)

### Community 89 - "Community 89"
Cohesion: 0.18
Nodes (9): _edge(), _elevenlabs(), make_voices(), punctuated(), _recorded(), recording(), _words_from_chars(), measure() (+1 more)

### Community 90 - "Community 90"
Cohesion: 0.17
Nodes (8): _comment_state(), post_comment(), published(), _record(), set_youtube_thumbnail(), _youtube_state(), _run_scheduled_comment(), video_youtube_comment()

### Community 91 - "Community 91"
Cohesion: 0.14
Nodes (9): _audio_48k(), _channel(), channel_name(), _channels(), _comment_after_upload(), fb_can_schedule(), upload(), _upload_facebook() (+1 more)

### Community 92 - "Community 92"
Cohesion: 0.18
Nodes (10): demucs_available(), _lines(), save_lines(), load(), _size(), Source, make_song(), sync_lyrics() (+2 more)

### Community 93 - "Community 93"
Cohesion: 0.16
Nodes (9): full_song(), _tag(), upload_text(), src(), test_description_layout(), test_hook_first_title_with_the_song_name(), test_no_ai_credit_when_the_song_has_none(), test_song_name_dropped_when_too_long() (+1 more)

### Community 94 - "Community 94"
Cohesion: 0.22
Nodes (9): _backdrop(), _centred(), draw(), _fit(), _font(), _picture(), _rounded(), _wrap() (+1 more)

### Community 95 - "Community 95"
Cohesion: 0.22
Nodes (10): apply(), avoid(), catalog(), clean(), pick(), suggest(), test_a_tradition_puts_its_traits_first_and_plain_anime_changes_nothing(), test_suggestion_follows_the_mood() (+2 more)

### Community 96 - "Community 96"
Cohesion: 0.14
Nodes (10): _alpha_over(), _backing(), block(), build_karaoke_ass(), dialogue(), enter(), karaoke(), _neon_title() (+2 more)

### Community 97 - "Community 97"
Cohesion: 0.21
Nodes (11): anime_tags(), full_prompt(), looks_like_prose(), _tidy(), test_a_frame_shape_inside_the_subject_does_not_remove_the_subject(), test_anime_tags_leaves_tags_alone_and_remembers_a_conversion(), test_delivery_instructions_are_dropped_and_the_two_people_counted(), test_empty_space_for_the_lyrics_does_not_ask_for_writing() (+3 more)

### Community 98 - "Community 98"
Cohesion: 0.23
Nodes (11): read(), _span(), split_hashtags(), spoken(), test_beats_skip_title_rows_and_strip_cues_and_loop_marker(), test_episodes_titles_and_hashtags(), test_misplaced_loop_marker_and_missing_time_are_noted(), test_round_trip_and_episode_picking() (+3 more)

### Community 99 - "Community 99"
Cohesion: 0.12
Nodes (16): with, args, cache, cache-dependency-path, if-no-files-found, includeUpdaterJson, name, node-version (+8 more)

### Community 100 - "Community 100"
Cohesion: 0.24
Nodes (11): choose(), best_of(), candidates(), claim(), one(), pictures_for(), release(), fetch() (+3 more)

### Community 101 - "Community 101"
Cohesion: 0.14
Nodes (9): local_card(), local_kind(), local_query(), plan_card(), plan_queries(), _subjects(), _entry(), test_graphic_and_montage_scenes_are_told_apart_without_claude() (+1 more)

### Community 102 - "Community 102"
Cohesion: 0.13
Nodes (10): project_path(), art_real(), auto_footage(), AutoFootageRequest, _cover_image(), filmstrip(), _media_info(), pick_footage() (+2 more)

### Community 103 - "Community 103"
Cohesion: 0.20
Nodes (7): base_size(), cache_file(), drawn(), _flat(), generate(), _ip_adapter(), _reference_image()

### Community 104 - "Community 104"
Cohesion: 0.22
Nodes (6): post_body(), best_cover_frame(), cover_score(), make_cover(), metadata(), write()

### Community 105 - "Community 105"
Cohesion: 0.23
Nodes (7): _impact(), impact_track(), _lowpass(), sound(), _thunder(), _whoosh(), _write()

### Community 106 - "Community 106"
Cohesion: 0.19
Nodes (8): device(), drop_parked(), _empty_cache(), _load(), outpaint(), _scheduler(), unload(), unload_later()

### Community 107 - "Community 107"
Cohesion: 0.24
Nodes (5): journey(), _context(), set_title(), suggest_posts(), write_post()

### Community 108 - "Community 108"
Cohesion: 0.21
Nodes (7): _ensure_server(), _meta_json(), PublishError, _rupload(), start_connect(), _upload_instagram(), publish_connect()

### Community 109 - "Community 109"
Cohesion: 0.17
Nodes (8): _short_idle(), shorts_apply(), shorts_edit(), shorts_remove_clip(), shorts_trim_beat(), ShortsApply, ShortsEdit, ShortsTrim

### Community 110 - "Community 110"
Cohesion: 0.18
Nodes (11): devDependencies, @tauri-apps/cli@^2, name, private, scripts, build, build:engine, build:ffmpeg (+3 more)

### Community 111 - "Community 111"
Cohesion: 0.29
Nodes (3): list_voices(), synthesize(), _synthesize()

### Community 112 - "Community 112"
Cohesion: 0.25
Nodes (8): default_seed(), _draw_job(), log(), step(), draw_picture(), _draw_state(), DrawReq, draw_checked()

### Community 113 - "Community 113"
Cohesion: 0.20
Nodes (7): bricolage, metadata, noto, notoKhmer, APPEARANCE_SCRIPT, SIZE_KEY, THEME_KEY

### Community 115 - "Community 115"
Cohesion: 0.20
Nodes (5): nextConfig, candidates, child, python, root

### Community 117 - "Community 117"
Cohesion: 0.25
Nodes (4): _Capture, _run(), log(), parse()

### Community 118 - "Community 118"
Cohesion: 0.25
Nodes (5): _account(), _json(), _meta_account(), _pages(), _token()

### Community 119 - "Community 119"
Cohesion: 0.25
Nodes (6): connected(), _tiktok_call(), tiktok_creator(), _check_channel(), publish_video(), tiktok_creator()

### Community 120 - "Community 120"
Cohesion: 0.22
Nodes (8): bundle, resources, windows, installerHooks, engine-dist/engine/, ffmpeg-dist/, $schema, nsis

### Community 121 - "Community 121"
Cohesion: 0.25
Nodes (6): _guidance_until(), callback(), _report(), _run(), test_a_picture_draw_reports_its_steps(), fake()

### Community 122 - "Community 122"
Cohesion: 0.25
Nodes (7): concurrency, cancel-in-progress, group, jobs, name, permissions, contents

### Community 123 - "Community 123"
Cohesion: 0.38
Nodes (3): plan_shots(), Shot, _snap()

### Community 124 - "Community 124"
Cohesion: 0.43
Nodes (3): _clock(), _jpegs(), rank()

### Community 125 - "Community 125"
Cohesion: 0.29
Nodes (4): _background_prompt(), suggest_background_prompt(), prompt_for(), test_every_picture_prompt_carries_the_house_look()

### Community 127 - "Community 127"
Cohesion: 0.29
Nodes (4): _cover_ms(), settings(), _upload_tiktok(), _settings()

### Community 128 - "Community 128"
Cohesion: 0.29
Nodes (7): dependencies, lucide-react@^1.52.0, next@16.3.8, react@19.2.8, react-dom@19.2.8, next, react-dom

### Community 129 - "Community 129"
Cohesion: 0.29
Nodes (6): bundle, macOS, targets, minimumSystemVersion, signingIdentity, $schema

### Community 130 - "Community 130"
Cohesion: 0.40
Nodes (3): cold_open_window(), _repeats(), song_slots()

### Community 131 - "Community 131"
Cohesion: 0.33
Nodes (5): eslintConfig, eslint@^9, eslint-config-next@16.3.8, eslint, eslint-config-next

### Community 132 - "Community 132"
Cohesion: 0.33
Nodes (6): scripts, build, dev, dev:engine, dev:web, lint

### Community 133 - "Community 133"
Cohesion: 0.33
Nodes (6): defaults, name, runs-on, run, build, shell

### Community 134 - "Community 134"
Cohesion: 0.33
Nodes (6): strategy, name, os, include, fail-fast, matrix

### Community 135 - "Community 135"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

### Community 137 - "Community 137"
Cohesion: 0.40
Nodes (3): _no_people(), _sex_negative(), _sexes()

### Community 138 - "Community 138"
Cohesion: 0.40
Nodes (5): steps, if, name, run, uses

### Community 139 - "Community 139"
Cohesion: 0.40
Nodes (5): GITHUB_TOKEN, KEY, TAURI_SIGNING_PRIVATE_KEY, TAURI_SIGNING_PRIVATE_KEY_PASSWORD, env

### Community 140 - "Community 140"
Cohesion: 0.50
Nodes (4): tags, True, push, workflow_dispatch

### Community 141 - "Community 141"
Cohesion: 0.50
Nodes (3): bundle, createUpdaterArtifacts, $schema

## Knowledge Gaps
- **27 isolated node(s):** `shorts-studio`, `Topic to video pipeline (Gemini, Edge TTS, Pexels, FFmpeg)`, `Data folder and locations.json storage`, `Installer builds and GitHub release workflow`, `Excel content plan import` (+22 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1360 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `duration()` connect `Community 92` to `Core Web API`, `Folder & Path Settings`, `Footage & Clip Picking`, `Longform Settings`, `Drafts & Art Status`, `Lyrics Alignment`, `Beats & Pipeline Art`, `Campaign Backend`, `Longform Storyboard`, `Community 48`, `Community 60`, `Community 67`, `Community 73`, `Community 77`, `Community 83`, `Community 87`, `Community 88`, `Community 89`, `Community 90`, `Community 91`, `Community 94`, `Community 102`, `Community 127`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `shorts-studio`, `Topic to video pipeline (Gemini, Edge TTS, Pexels, FFmpeg)`, `Data folder and locations.json storage` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Core Web API` be split into smaller, more focused modules?**
  _Cohesion score 0.04219725343320849 - nodes in this community are weakly interconnected._
- **Why does `draw_magazine()` connect `Community 81` to `Drafts & Art Status`, `Community 80`, `Song Generation`, `Community 57`, `Beats & Pipeline Art`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Should `Campaign UI` be split into smaller, more focused modules?**
  _Cohesion score 0.04215597711532671 - nodes in this community are weakly interconnected._
- **Why does `VideoScript` connect `Community 78` to `Core Web API`, `Campaign Clips & Highlights API`, `Drafts & Art Status`, `Community 107`, `Community 46`, `Community 83`, `Longform Storyboard`, `Song Generation`, `Community 87`, `Community 57`, `Beats & Pipeline Art`, `Community 60`, `Community 62`, `Community 63`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Should `Folder & Path Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.05627705627705628 - nodes in this community are weakly interconnected._