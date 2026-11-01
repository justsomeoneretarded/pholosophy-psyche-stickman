"""Original instrumental score with ACE-Step 1.5 (MIT) on a CPU runner.

python audio/music.py <ACE-Step checkout> <film.json> <output.wav>

The prompt comes from film["music"]["prompt"]. Any failure leaves no file and the mix
falls back to the synthesized bed, so a render never fails because of music.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

DEFAULT_PROMPT = ("emotional solo felt piano, slow and intimate, sparse melancholic chords, gradually building "
                  "with soft strings into a hopeful ending, cinematic, 72 bpm, instrumental")


def notice(title, message, level='notice'):
    print(f"::{level} title={title}::{message.replace(chr(10), '%0A')}", flush=True)


def main() -> int:
    root, film_path, output = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    film = json.loads(film_path.read_text())
    seconds = min(float(os.environ.get('ACE_SCORE_SECONDS','45')), sum(s['dur'] for s in film['shots']) + 2)
    prompt = (film.get('music') or {}).get('prompt') or DEFAULT_PROMPT
    sys.path.insert(0, root)
    try:
        from acestep.handler import AceStepHandler
        from acestep.inference import GenerationConfig, GenerationParams, generate_music
        started = time.time()
        dit = AceStepHandler()
        status, ok = dit.initialize_service(project_root=root, config_path='acestep-v15-turbo', device='cpu')
        if not ok:
            raise RuntimeError(f'initialize_service: {status}')
        work = output.parent / 'ace-output'
        params = GenerationParams(caption=prompt, instrumental=True, lyrics='[Instrumental]',
                                  duration=seconds, inference_steps=8, seed=7, thinking=False)
        result = generate_music(dit, None, params, GenerationConfig(batch_size=1, audio_format='wav'), save_dir=str(work))
        if not result.success:
            raise RuntimeError(result.error)
        produced = sorted(work.rglob('*.wav'), key=lambda p: p.stat().st_size)
        if not produced:
            raise RuntimeError('no audio written')
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(produced[-1], output)
        shutil.rmtree(work, ignore_errors=True)
        notice('Score', f'{seconds:.0f}s generated in {(time.time() - started) / 60:.1f} min. Prompt: {prompt}')
    except Exception as exc:  # noqa: BLE001 -- the synthesized bed is the fallback
        notice('Score unavailable', f'{type(exc).__name__}: {str(exc)[:500]}; the synthesized fallback will be used.', 'warning')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
