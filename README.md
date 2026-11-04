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

The latest [reviewed full-length production](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41687663919) is **5:46.7, native 1920×1080 at 30 FPS, H.264/AAC**. [Download the video and publishing package](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41687663919/artifacts/13256373117) (277 MB; retained until 10 November 2026). It includes 42 verified narration passages, subtitles, original music, effects, thumbnails and research/metadata files. Full decode passed; integrated loudness is −14 LUFS and true peak −1.8 dBFS.

This episode is an **AI editorial revision made during autonomous output review**, independently reviewed by a separate model. It is not evidence that unattended title-only writing consistently passes. Its final review has no confirmed major findings; minor preferences remain recorded. Actual decoded MP4 snapshots were inspected for phone text, distinct characters, seated interactions, captions and the end card. Audio was checked using transcription, timing and loudness; direct listening was unavailable.

Measured narration gaps fell from a median of about five seconds in the earlier revision to one second. Thirty exact verified takes were reused, twelve new takes were generated, and all 42 were transcribed again. A real renderer preflight verifies repeatable pixels after font loading and canvas-state reset.

The [51.43-second procrastination smoke test](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41341468260) also passed the complete pipeline. It uses an explicitly authored regression fixture. The [253.47-second philosophical rerender](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41634684988) verified corrected sketch contact and cast/recipient acting, but its passive script did not receive editorial acceptance.

The [fresh philosophical writing benchmark](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/41690434123) failed during editorial repair: unsupported props/actions, followed by a local model output-budget failure. Repair requests now receive the complete supported rig contract; the follow-up benchmark remains a separate test, not a finished narrated production.

Production rig coverage includes planted walk/run cycles, stopping, drawing with a visible pen/page, showing/reading a book, conversation, thinking and articulated chair transitions. Numerical tests check actual IK pen endpoints, planted feet and distinct seat allocation. Complex arbitrary pickup/handover, collision-free blocking in every environment, vertical production, full local-only long-form writing, optional YouTube upload and consistent unattended editorial quality are not certified.

[Detailed production evidence and limitations](docs/review-2026-11-04.md).
