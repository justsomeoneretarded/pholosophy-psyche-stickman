# Validation status

## Verified on GitHub-hosted Ubuntu

- [51 tests passed](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/39924125890), including real FFmpeg encoding/decoding, IK segment lengths, planted feet, sitting, shared handshake contact, reachable prop grip, phrase alignment, PCM resampling and content gates.
- [Motion diagnostic run](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/39923026883): 35 seconds, 1050 frames, native 1280×720, 30 FPS; render time **5.8291 seconds**. A later repeated run measured 7.6457 seconds. Performance varies by runner.
- [Integrated production smoke](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/39923854262): **39.2477 seconds**, 1177 frames, native **1920×1080 at 30 FPS**. Render time **13.1154 seconds**. Piper narration, Whisper CPU INT8 verification, synchronized captions, multiple articulated scenes, original procedural music/effects, thumbnail, metadata and QA all completed. Final MP4 passed FFprobe checks and full FFmpeg decode.
- [Download the verified publishing package](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/39923854262/artifacts/12488312183). Artifact expires after 14 days.
- This integrated test used the fixed editorial fixture in examples/procrastination-smoke.json. **It does not establish autonomous Qwen writing quality.**
- Observed runner resources: four CPUs, about 15 GiB total memory. One acceptance runner exposed 86 GB free on a larger root filesystem; production targets GitHub's documented 14 GB temporary-storage baseline and does not assume that extra space.

## Failures found and fixed

1. Initial acceptance workflow lacked FFmpeg; generation never began. Explicit system installation was added.
2. PyAV 19 removed the metadata_errors argument used by faster-whisper 1.2.1. Dependency was constrained below 17 and speech verification now decodes PCM with FFmpeg explicitly. The integrated smoke subsequently passed.
3. Visual review found vertical prop target coordinates scaled with canvas width. Coordinates now use aspect-correct units and a crouching reach; an actual grip-position test passes.
4. The original handshake demo merely waved. Paired characters now share a contact target and approach with the walk cycle; a contact regression test passes.
5. A temporary lightweight CI edit assumed FFmpeg was preinstalled. That run failed; explicit installation was restored. Failed history remains visible.

## Still pending

- Current title-only workflow: [run](https://github.com/justsomeoneretarded/pholosophy-psyche-stickman/actions/runs/39924477496).
- AI-written procrastination smoke and the two distinct six-minute narrative tests.
- Measured Qwen generation speed, reliability and script quality.
- Chatterbox Nano/Turbo CPU comparison, custom voice and optional private YouTube upload.
- Comprehensive collision/contact, text-overlap, frozen-acting and artistic-continuity validation.

The workspace repeatedly lost connectivity during model downloads. Code and testing continued through GitHub APIs and Actions. Interrupted local downloads are not model benchmarks. The obsolete acceptance run using the incompatible decoder was cancelled explicitly; current acceptance and title-only runs were dispatched with the corrected implementation.

A workflow file is not evidence that a production passed. Only successful runs with verified final outputs are listed as completed.
