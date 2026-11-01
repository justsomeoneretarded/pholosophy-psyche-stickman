"""Voice-over with Chatterbox Turbo (CPU) for every narrator line in a film, fitted to the shots.

python audio/voice.py build/film.json build/voice [--narrator warguy|kit-laser|female]

For each line with who == "narrator" (and its optional twist) this records the narration with the
chosen narrator reference, checks it with faster-whisper (re-recording garbled lines once),
stretches the shot if the voice needs more time, sets the caption typing speed to match, and
records "voice_file" / "voice_dur" in the line. The film JSON is rewritten in place.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.speech.narrator import Narrator, verify, wav_seconds  # noqa: E402

GAP = .4          # pause between a line and its twist


def notice(title, message, level='notice'):
    print(f"::{level} title={title}::{message.replace(chr(10), ' ')[:900]}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('film'); ap.add_argument('out')
    ap.add_argument('--narrator', default='warguy')
    ap.add_argument('--whisper', default='base.en')
    a = ap.parse_args()
    film_path, out_dir = Path(a.film), Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    film = json.loads(film_path.read_text())
    jobs = [(i, k, ln) for i, s in enumerate(film['shots']) for k, ln in enumerate(s.get('lines') or []) if ln.get('who') == 'narrator']
    if not jobs:
        notice('Voice-over', 'no narrator lines in this film')
        return 0
    started = time.time()
    voice = Narrator(a.narrator)
    import numpy as np
    import soundfile as sf

    def record(text, path, seed=0):
        delivery = 'dramatic' if text.rstrip().endswith('!') else 'calm'
        return voice.speak(text, path, delivery, seed=seed)

    takes = []
    for n, (i, k, ln) in enumerate(jobs):
        main_path = out_dir / f'vo-{i:03d}-{k}-a.wav'
        record(ln['text'], main_path)
        twist_path = None
        if ln.get('twist'):
            twist_path = out_dir / f'vo-{i:03d}-{k}-b.wav'
            record(ln['twist'], twist_path)
        takes.append((i, k, ln, main_path, twist_path))
        if n % 5 == 0:
            print(f'narration {n + 1}/{len(jobs)}  {(time.time() - started) / 60:.1f} min', flush=True)
    voice.close()
    # Check what was said; re-record lines that came out garbled.
    try:
        from faster_whisper import WhisperModel
        whisper = WhisperModel(a.whisper, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1)
        bad = []
        for i, k, ln, p1, p2 in takes:
            score, _ = verify(p1, ln['text'], whisper)
            ln['speech_check'] = round(score, 3)
            if score < .8:
                bad.append((i, k, ln, p1))
        del whisper
        if bad:
            voice = Narrator(a.narrator)
            for i, k, ln, p1 in bad:
                record(ln['text'], p1, seed=5)
            voice.close()
            notice('Narration re-recorded', f'{len(bad)} lines scored below 0.8 and were recorded again')
    except Exception as exc:  # noqa: BLE001 -- verification is a safety net, not a requirement
        notice('Speech check skipped', f'{type(exc).__name__}: {str(exc)[:200]}', 'warning')
    # Join line + twist, fit the shots and the caption speed to the voice.
    for i, k, ln, p1, p2 in takes:
        a1, sr = sf.read(str(p1), dtype='float32')
        parts = [a1]
        if p2:
            a2, _ = sf.read(str(p2), dtype='float32')
            parts += [np.zeros(int(GAP * sr), np.float32), a2]
        audio = np.concatenate(parts)
        name = f'vo-{i:03d}-{k}.wav'
        sf.write(str(out_dir / name), audio, sr)
        dur = len(audio) / sr
        ln['voice_file'] = name
        ln['voice_dur'] = round(dur, 3)
        ln['cps'] = round(max(9.0, len(ln['text']) / max(.4, len(a1) / sr * .92)), 2)
        if p2:
            ln['twist_at'] = round(len(a1) / sr + GAP, 3)
        shot = film['shots'][i]
        need = (ln.get('at') or 0) + dur + .55
        if shot['dur'] < need:
            shot['dur'] = round(need, 2)
    film['duration'] = round(sum(s['dur'] for s in film['shots']), 2)
    film['narrator_voice'] = a.narrator
    film_path.write_text(json.dumps(film, indent=1, ensure_ascii=False))
    spoken = sum(t[2]['voice_dur'] for t in takes)
    notice('Voice-over', f'{len(jobs)} narrator lines, {spoken:.0f}s of speech ({a.narrator}) in {(time.time() - started) / 60:.1f} min; '
                         f'film is now {film["duration"] / 60:.1f} min')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
