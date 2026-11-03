# Stickman philosophy & psychology studio

Enter a title or concept to generate a narrated vector animation with articulated characters, expressive faces, procedural environments, sound design and publishing files. Stories can use ordinary situations, visual metaphors, contrasting examples and an optional inner voice. Production runs on GitHub Actions with free model access; GitHub and model-provider usage limits still apply.

## Make a video

1. **Actions → Generate Stickman Video → Run workflow** (branch `main`).
2. Fill in: **Title** (e.g. `Addiction`), **Narrator** (Warguy by default, Kit Laser or Female), **Length** (6 minutes by default, or Auto), and optional **Notes** to steer the story.
3. Download **philosophy-video** from the run's Artifacts: `video.mp4`, three thumbnails and `thumbnail.png`, `subtitles.srt` / `subtitles.vtt`, titles, description, tags, pinned comment, `script.txt`, `story.md`, `storyboard.json`, `scene_timeline.json`, research files, `speech-verification.json`, `quality_report.json` and a contact sheet.

A free Groq API key in repository secret `GROQ_API_KEY` enables hosted writing. Local Ollama Qwen3 4B is the CPU fallback; complete local-only long-form writing remains unverified. Free-provider rate limits can stop a run.

## How a film is made

| Job | What runs |
|---|---|
| Write and storyboard | Topic-aware Wikipedia and PubMed metadata; **gpt-oss-20b on free Groq**, with 120b/Qwen and local fallbacks, develops the narrative. A separate reviewer critiques it. Supported physical directions compile into rig performances; experimental AI shot generation can be selected with `STORYBOARD_MODELS`. `story/essay.py` |
| Record the narration | **Chatterbox Turbo** (CPU) with the chosen narrator reference; faster-whisper checks every line; shots stretch to fit the voice. `audio/voice.py` |
| Compose the score | **ACE-Step 1.5** attempts a 45-second CPU score from the writer's prompt, looped with crossfades. An original procedural piano bed is used if generation fails. The previous 240-second setting exceeded the upstream 600-second timeout in one run. `audio/music.py` |
| Picture | The canvas engine (`engine/`) renders the film in four parallel parts with headless Chromium. |
| Sound, edit and package | Sound effects and ambience from what happens on screen, music ducking under voices, -14 LUFS master (`audio/sound.py`); thumbnails and publishing files (`story/package.py`); a review copy on the `previews` branch. |

Ordinary title-driven runs create a new script. Explicit regression fixtures are kept separately and are not evidence of fresh AI writing. Each shot is composed from the engine's vocabulary (`engine/vocab.json`): named sets with time of day and weather, supported articulated performances and facial moods, props and held objects, phone screens (chat, calls, feed, alarm, power off), notes, calendars, photos, speech bubbles and thoughts, the inner voice, counters and day chapters, big words, colour grades, and wide / medium / close / extreme / two-shot / phone / insert framing. `story/validate.py` repairs anything the engine cannot draw.

The writer now generates a compact outline and expands it in bounded requests, then saves editorial critiques and focused revisions. Quoted fictional speech and self-talk are allowed in narration. Unsupported attributed quotations are still rejected.

Speech verification covers the main line and any twist. Disputed takes receive an independent `small.en` transcription without supplying the script as a recognition prompt. Failed takes are regenerated and checked again; changed negations remain a failure. Caption wording always comes from the script, with ASR timestamps where available and explicitly marked interpolation otherwise.

The production canvas rig has world-space planted stance feet, continuous acceleration, two-bone limb IK, scale-aware seating, support geometry for otherwise unsupported sitting, expressive faces and hand-attached held items. Clean thumbnail passes remove video captions and counters before applying the thumbnail headline.

### Preview locally

```bash
npm install && npx playwright install chromium
node render/render.mjs --film build/film.json --stills build/stills --every 3 --width 960
```

## Production rig inspection

`examples/rig-review.json` is rendered by the same canvas engine as generated films. The **Inspect production rig in motion** workflow exports a playable clip and real frame snapshots for walking, running, seated acting, falling/recovery, drinking and two-character gestures. This is separate from the legacy Python showcase below.

[Review evidence and known limits](docs/review-2026-11-01.md) records actual runs and distinguishes successful encoding from editorial or animation quality.

## Legacy Python animation engine

The noir style (`pipeline/animation/noir.py`) sits on top of a general acting engine, which is also used by the older colourful style and the acting showcase (`python -m scripts.demo`).

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

## Licences

Code: GPL-3.0-or-later. Fonts: SIL Open Font License (see `assets/fonts`). Current production music: ACE-Step-generated score, with an original procedural piano/pad fallback and synthesized effects. The legacy Python asset library also contains Scott Buckley music under CC BY 4.0 (see `assets/music`). Narrator reference clips in `assets/voices` are excerpts published with the owner's approval. Chatterbox (MIT) adds an inaudible watermark to generated speech.

## Verified outputs and review limits

The [51.43-second production smoke test](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41341468260) passed with native 1920×1080/30 FPS H.264/AAC, verified Chatterbox narration, captions, procedural music/effects, thumbnails and metadata. Its script is an explicitly authored regression fixture, not a title-only writing benchmark.

The [253.47-second philosophical rerender](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41341144570) passed encoding and speech checks, but retains an excessive-idle-acting warning and weak editorial passages. It is review evidence, not artistic acceptance. Final-MP4 snapshots exposed recipient/action and cast-identity problems that prompted further corrections.

[Encoded-output inspection](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41634124340) now publishes decoded MP4 frames beside each run on the previews branch. [The fresh six-minute production review](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41634217001) is a separate test; check its conclusion before assuming a full-length video exists.

Production rig coverage includes drawing with a visible pen and page, showing/reading a book, conversation, thinking and articulated chair transitions. Numerical tests check actual rendered IK pen endpoints, planted feet and distinct seat allocation. Complex arbitrary pickup/handover, collision-free blocking in every composed environment, vertical production, full local-only writing, and consistent editorial quality are not certified.
