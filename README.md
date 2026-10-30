# Stickman philosophy & psychology studio

Type a topic, get a finished minimalist stickman video essay: black, white and grey, faceless figures, a spotlight, film grain, and one warm amber colour for moments of meaning. Narration where an idea needs explaining; silent passages with music and image elsewhere. Everything runs free on GitHub Actions.

## Make a video

1. **Actions → Generate Stickman Video → Run workflow** (branch `main`).
2. Fill in the form:
   - **Title**, e.g. `Nihilism - belief in nothing`
   - **Narrator**: Warguy (default), Kit Laser or Female
   - **Length**: Auto (default, the writer chooses, usually 5-8 minutes) or a number of minutes
   - **Format**: 16:9 or 9:16; optionally burn captions into the picture
3. When the run finishes, download **philosophy-video** from the run's Artifacts.

One-time setup: a free Groq API key in the repository secret `GROQ_API_KEY`.

### What's in the package

`video.mp4` (1080p, 30 fps, -14 LUFS), `thumbnail-01..03.jpg`, `subtitles.srt/.vtt`, `recommended-title.txt`, `title-options.txt`, `description.txt` (with music credit), `tags.txt`, `pinned-comment.txt`, `script.txt`, `sources-and-credits.txt`, `contact-sheet.jpg` and `review.html`.

## How it works

| Job | What runs | Notes |
|---|---|---|
| plan | Wikipedia background reading, then **qwen3.8-27b on Groq** writes the script as beats | Falls back to **gpt-oss-120b on Groq**, then **Gemma 4 12B** locally via Ollama |
| music | **ACE-Step 1.5** (MIT) composes a contemplative and a hopeful score | Runs in parallel; falls back to bundled Scott Buckley tracks (CC BY 4.0, credited automatically) |
| voice | **Chatterbox Turbo** on CPU with the chosen narrator reference; **faster-whisper** checks every line | Dramatic lines use the expressive Chatterbox model; failed lines are re-recorded |
| produce | The animation engine renders every beat in parallel; music swells in silent beats and ducks under the voice; two-pass loudness to -14 LUFS | Thumbnails, metadata, review page and video checks |

### The script

The writer returns **beats**. Each beat is *narrated* (voice-over) or *silent* (music and picture, at most one line of on-screen text), and picks one of 20 symbolic set pieces with a few labels:

`word_wall`, `routine_loop`, `crowd`, `pillar`, `fall`, `desert`, `shadow_companion`, `sisyphus`, `chalk_door`, `chains`, `giant_hand`, `stairs`, `doors`, `mirror`, `scale`, `flower`, `title_card`, `thinker`, `clock`, `cage`

The set piece supplies the staging and camera (`pipeline/animation/setpieces.py`), so the language model never choreographs joints. Scripts are rejected and rewritten if they invent quotes, statistics or "studies show" claims, miss the length, or overuse a set piece. `examples/nihilism-script.json` is a hand-written example; run the plan stage with `--script` to use a fixed script.

### Run locally

```bash
pip install -r requirements-core.txt
python -m pipeline.essay plan --title "Nihilism - belief in nothing" --script examples/nihilism-script.json
# voice needs CPU torch 2.6.0 + requirements-voice.txt
python -m pipeline.essay voice --narrator warguy
python -m pipeline.essay produce --quality standard
```

## Animation engine

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

Code: GPL-3.0-or-later. Fonts: SIL Open Font License (see `assets/fonts`). Music fallback: Scott Buckley, CC BY 4.0 (see `assets/music`). Narrator reference clips in `assets/voices` are excerpts published with the owner's approval. Chatterbox (MIT) adds an inaudible watermark to generated speech.
