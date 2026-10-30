"""Generate an original instrumental score with ACE-Step 1.5 on the CPU runner.

Usage: python scripts/generate_music.py <ACE-Step checkout> <mood> <seconds> <output.wav>
Moods: contemplative (default) or hopeful. Any failure leaves no file, so production
falls back to the bundled licensed tracks in assets/music.
"""
import shutil
import sys
import time
from pathlib import Path

PROMPTS = {
    'contemplative': 'slow contemplative ambient film score, sparse felt piano, soft sustained strings, low warm drone, '
                     'melancholic and introspective, minimalist, gentle reverb, no drums, no vocals',
    'hopeful': 'slow hopeful ambient film score, warm felt piano melody, soft rising strings, gentle and tender, '
               'minimalist, quiet resolution, no drums, no vocals',
}


def notice(title, message, level='notice'):
    print(f"::{level} title={title}::{message.replace(chr(10), ' ')}", flush=True)


def main():
    root, mood, seconds, output = sys.argv[1], sys.argv[2].strip().lower(), float(sys.argv[3]), Path(sys.argv[4])
    caption = PROMPTS.get(mood, PROMPTS['contemplative'])
    sys.path.insert(0, root)
    try:
        from acestep.handler import AceStepHandler
        from acestep.inference import GenerationConfig, GenerationParams, generate_music
        started = time.time()
        dit = AceStepHandler()
        status, ok = dit.initialize_service(project_root=root, config_path='acestep-v15-turbo', device='cpu')
        if not ok:
            raise RuntimeError(f'initialize_service: {status}')
        work = output.parent / f'ace-{mood}'
        params = GenerationParams(caption=caption, instrumental=True, lyrics='[Instrumental]',
                                  duration=seconds, inference_steps=8, seed=7 if mood == 'contemplative' else 11, thinking=False)
        result = generate_music(dit, None, params, GenerationConfig(batch_size=1, audio_format='wav'), save_dir=str(work))
        if not result.success:
            raise RuntimeError(result.error)
        produced = sorted(work.rglob('*.wav'), key=lambda p: p.stat().st_size)
        if not produced:
            raise RuntimeError('no audio written')
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(produced[-1], output)
        shutil.rmtree(work, ignore_errors=True)
        notice('Score', f'{mood}: {seconds:.0f}s generated in {(time.time() - started) / 60:.1f} min')
    except Exception as exc:  # noqa: BLE001 -- bundled music remains the fallback
        notice('Score unavailable', f'{type(exc).__name__}: {str(exc)[:400]}; bundled music will be used', 'warning')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
