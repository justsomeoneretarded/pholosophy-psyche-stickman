# Stickman psychology & philosophy studio

CPU-only, local-model video production with an original articulated stickman rig. **Production core verified with a 39-second native 1080p smoke test; autonomous long-form generation remains under validation.** [Validation status](docs/VALIDATION.md) separates observed results from untested features.

## One-title quick start

1. Open **Actions → Generate Stickman Video → Run workflow**.
2. Enter a title, such as **Why Smart People Overthink Everything**; leave defaults.
3. Open the successful run and download **stickman-video-output** under Artifacts.
4. Extract the archive and use `video.mp4` for upload.

Failures upload **failed-production-diagnostics**, not a successful package. A failed-run MP4 is not an approved production. GitHub login is generally required to download artifacts.

Default: native 1920×1080, 30 FPS, H.264/AAC, approximately six minutes. Workflow duration accepts 4–10 minutes. Measured narration must fall within 22% of target, or the run stops before rendering. CLI permits 0.5-minute tests. Vertical output renders natively at 1080×1920, reflows text and uses its own canvas; staging remains experimental.

[Download the verified smoke-test video and publishing package](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/39923854262/artifacts/12488312183). This test uses a fixed editorial fixture to isolate production; AI writing is tested separately.

## Architecture

```mermaid
flowchart TD
 A[One title] --> B[Crossref bibliographic retrieval]
 B --> C[Local Qwen3 4B outline and scene writing]
 C --> D[Pydantic validation and originality checks]
 D --> E[Piper scene narration]
 E --> F[faster-whisper CPU INT8 verification]
 F --> G[Measured timing and phrase anchors]
 G --> H[Articulated IK animation and environments]
 H --> I[Stream native frames to FFmpeg segments]
 I --> J[Original procedural audio and ducked mix]
 J --> K[MP4, captions, thumbnail and metadata]
 K --> L[FFprobe, full decode and file checks]
 L --> M[Actions artifact]
```

Python handles orchestration and animation. The custom Pillow renderer samples a deterministic timeline and streams frames directly to FFmpeg. There is no browser or uncompressed frame archive. This is an engineering baseline, **not a benchmark-proven superiority claim over Remotion**.

### Acting engine

Characters are directed, not posed. The writer lists actions with a target and an emotion; the acting planner (`pipeline/animation/acting.py`) turns them into a continuous performance:

- **Movement** — walking, running, sneaking, pacing, entering, leaving (off stage or through a door), climbing stairs, sitting, lying down, falling and getting up. Characters walk to whatever they are about to use or talk to, stand up before leaving a chair, and settle onto planted feet.
- **Interaction** — talk, argue, hug, comfort, handshake, high five, push, pull, give and chase. The partner reacts automatically: hugs are returned, a push knocks the other person back, talking makes them turn, listen and nod.
- **Environment** — sit on chairs, benches, sofas and beds, type at a computer, pick up, carry, hand over and drop objects, use a phone, read, drink, open doors, look out of windows, lean on walls and switch the lights off.
- **Emotion** — 14 emotions drive eyes, brows, mouth, blush, tears, sweat, anger marks and hearts, plus posture and gait (sad characters slump and walk slower, scared ones shrink and shiver, happy ones bounce). Emotion persists until it changes.
- **Life** — breathing, weight shifts, blinking and watching the other character between actions.
- **Camera** — an automatic editor cuts and pushes between establishing wide shots, two-shots for interactions and close-ups for emotional beats.

The rig (`pipeline/animation/rig.py`) uses two-bone IK with rigid limbs; hands move in arcs around the shoulder and limbs foreshorten while turning, so nothing snaps. The renderer (`pipeline/animation/scene.py`) draws 19 environments, 26 prop types and four distinguishable characters (main, friend, the purple "shadow" inner critic, the "future" self with glasses) at 2x supersampling.

Run `python -m scripts.demo` to render the acting showcase in `examples/acting-showcase.json` (eight scenes, about two minutes) with sound cues and motion QA.

The LLM emits validated data, never executable animation code. Actions, actors, props, time intervals and coordinates are checked. Scene filenames are restricted to safe identifiers. The title is passed as JSON environment data; it is never interpolated into shell commands.

## Install and run locally

Requires Python 3.12, FFmpeg/FFprobe, DejaVu Sans, and Ollama. Install FFmpeg and `fonts-dejavu-core` through the system package manager. Install Ollama from its official site.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m piper.download_voices en_US-ljspeech-high --download-dir .cache/voices
ollama serve
# Another terminal:
ollama pull qwen3:4b
python -m pipeline.main --title "Why We Procrastinate" --minutes 0.75 --out outputs/smoke
python -m pytest -q
python -m scripts.demo
```

The GitHub workflow installs dependencies automatically. Lightweight tests require no AI models; they include a real FFmpeg encode/decode. The demo exports a playable motion clip, contact sheet and reports using the production engine. **Production acceptance renders** runs the procrastination smoke test plus two distinct six-minute essay titles.

## Narration and alignment

Default: Piper `en_US-ljspeech-high`, one consistent English voice without reference audio. Its [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD) identifies the LJ Speech dataset as public domain. Piper code is GPL-3.0-or-later; weights are downloaded separately.

Change voices by downloading a permitted Piper ONNX model and setting `PIPER_VOICE` to its path, with its adjacent ONNX JSON config. `voice=custom` also requires `CUSTOM_VOICE_AUTHORIZED=true`. It means a custom Piper model, **not audio-reference cloning**. On GitHub the custom model must be supplied during setup. Normal auto narration needs no configuration.

Chatterbox Nano was not found under the PyPI name `chatterbox-nano`; that does not prove no such model exists. Chatterbox Turbo/Nano CPU inference and voice licensing were not benchmarked. Piper is the executable baseline, not the winner of an unperformed comparison.

Scene speech is checked with faster-whisper CPU INT8, word timestamps and normalized word agreement. Defective speech gets one bounded regeneration retry, then fails visibly. Speech agreement is not a pronunciation guarantee. Measured audio duration controls visual timing; exact phrase anchors refine actions when found. Subtitles follow verified transcription. Narration is never stretched to force duration.

## Visual and audio extensions

- Proportions, IK and the action vocabulary live in `pipeline/animation/rig.py`.
- Planning, gestures, interactions, emotions and object handling live in `pipeline/animation/acting.py`.
- Faces, environments, props, effects and the camera live in `pipeline/animation/scene.py`.
- `pipeline/production/director.py` adds any prop an action needs (a chair to sit on, a phone to pick up) and records the repair.
- Sound cues follow the planned performance, including automatic footsteps, in `pipeline/production/audio.py`. Any added recordings need documented license and attribution.
- Validated defaults live in `pipeline/config.py`.

## Research and originality limits

Crossref retrieves real DOI records and available abstracts. Bibliographic metadata does not verify claims. Current generation is therefore framed as **philosophical exploration**, not a verified scientific explanation. Writing prompts prohibit invented statistics, diagnosis, universal personality laws and attributed quotations. Prompts are not a factual verifier. `sources.json`, `claims.json` and research notes disclose the limitations.

Each title gets a fresh thesis, metaphor and outline. Scenes are written with narrative context. Persistent five-word-shingle overlap and major-scene-sequence checks reject substantial repetition. Hook/structure originality is imperfect, and cache eviction loses history; retain downloaded scripts for a durable editorial archive.

[YouTube monetization policy](https://support.google.com/youtube/answer/1311392) requires substantive originality across a channel. No monetization or virality guarantee is made.

## Delivery, QA and recovery

Successful artifacts include MP4, 1280×720 thumbnail, script, original/aligned storyboards, scene timeline, narration, SRT/VTT, captions, title/description, keywords, hashtags, pinned comment, metadata, sources, claims, research notes, audio licenses, speech/motion reports, quality report, production report/metrics, contact sheet, segments and `SUCCESS.json`.

Technical QA checks native resolution, codecs, FPS, duration, nonempty outputs and a complete FFmpeg decode. Motion sampling checks finite joints, rigid limb lengths, frame-to-frame continuity, floor contact and stage bounds. It **does not yet comprehensively detect** text overlap, wall penetration, every attachment failure, blank frames, frozen acting or artistic continuity. Those are gaps, not passing checks.

Repeat an identical local command and output path to reuse the original storyboard, matching speech chunks and hashed encoded segments. Different configurations need a new directory. Failure artifacts preserve checkpoints; download them into a matching local output directory to resume. Automatic cross-run restoration is not implemented. Inspect `FAILURE.txt`, speech verification, motion report and scene logs.

Models run sequentially. Ollama unloads after requests. Rendering uses two FFmpeg threads, bounded scene segments and streamed frames. Model caches can be evicted or exceed cache allowances. Successful artifacts expire after 14 days; failure diagnostics after seven. CPU writing/model downloads may dominate total runtime.

GitHub [documents](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) standard public Ubuntu runners at four CPUs, 16 GB RAM and 14 GB SSD. Workflows log observed resources. Public standard runners are currently free; private repositories have metered allowances. Check account usage, artifact storage and cache limits. No paid inference/rendering service is required.

## Optional YouTube upload

Disabled by default. Enable YouTube Data API v3 in a Google Cloud project, configure OAuth consent and authorize the official `youtube.upload` scope with a desktop OAuth client. Store authorized-user JSON in repository secret `YOUTUBE_OAUTH_JSON`, never in Git. Then enable the workflow upload input.

The official API uploader always uses **private** visibility. Completed and pending markers guard retries in the same output directory. An ambiguous failure needs checking in YouTube Studio before retrying. Cross-run duplicate lookup, scheduling, public publishing and thumbnail upload are not implemented. OAuth testing-token expiry, API quota and project audit restrictions still apply.

## License

Original code, procedural music and sound effects: GPL-3.0-or-later. Dependencies, model weights and system fonts retain their own terms. See `LICENSE`, `THIRD_PARTY.md`, model cards and per-run audio licenses. No copyrighted character assets are bundled.
