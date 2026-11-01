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
from pipeline.speech.caption_timing import align_caption_words  # noqa: E402

GAP = .4          # pause between a line and its twist


def notice(title, message, level='notice'):
    print(f"::{level} title={title}::{message.replace(chr(10), ' ')[:900]}", flush=True)


def verify_takes(takes, whisper, minimum=.8):
    """Check every spoken part, including twists; retain evidence for review."""
    records = []
    for i, k, line, main_path, twist_path in takes:
        parts = [('main', main_path, line['text'])]
        if twist_path:
            parts.append(('twist', twist_path, line['twist']))
        for part, path, expected in parts:
            agreement, words = verify(path, expected, whisper)
            records.append({'shot': i, 'line': k, 'part': part, 'file': str(path),
                            'expected': expected, 'agreement': round(agreement, 4),
                            'words': words, 'passed': agreement >= minimum})
    return records


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
    # Verification is required, and a retry must itself pass a fresh transcription.
    report_path = out_dir / 'verification.json'
    try:
        from faster_whisper import WhisperModel
        whisper = WhisperModel(a.whisper, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1)
        records = verify_takes(takes, whisper)
        report_path.write_text(json.dumps({'passed': all(r['passed'] for r in records), 'clips': records}, indent=2))
        bad = [r for r in records if not r['passed']]
        del whisper
        if bad:
            voice = Narrator(a.narrator)
            try:
                for r in bad:
                    record(r['expected'], Path(r['file']), seed=5)
            finally:
                voice.close()
            notice('Narration re-recorded', f'{len(bad)} spoken parts were regenerated; checking the new takes')
            whisper = WhisperModel(a.whisper, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1)
            records = verify_takes(takes, whisper)
            del whisper
        passed = all(r['passed'] for r in records)
        report_path.write_text(json.dumps({'passed': passed, 'clips': records}, indent=2))
        if not passed:
            failed = [f"{r['file']} ({r['agreement']:.2f})" for r in records if not r['passed']]
            raise RuntimeError('Narration still differs from the script after regeneration: ' + ', '.join(failed))
        for i, k, line, _, _ in takes:
            parts = [r for r in records if r['shot'] == i and r['line'] == k]
            line['speech_check'] = min(r['agreement'] for r in parts)
            line['speech_verified'] = True
        film['speech_verification'] = {'passed': True, 'parts': len(records), 'minimum_agreement': min(r['agreement'] for r in records)}
    except Exception as exc:
        report_path.write_text(json.dumps({'passed': False, 'error': f'{type(exc).__name__}: {exc}',
                                          'clips': locals().get('records', [])}, indent=2))
        raise RuntimeError('Speech verification did not pass; see voice/verification.json') from exc
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
        main_words = next(r['words'] for r in records if r['shot'] == i and r['line'] == k and r['part'] == 'main')
        ln['word_times'] = align_caption_words(ln['text'], main_words, len(a1) / sr)
        if p2:
            twist_words = next(r['words'] for r in records if r['shot'] == i and r['line'] == k and r['part'] == 'twist')
            offset = len(a1) / sr + GAP
            for word in align_caption_words(ln['twist'], twist_words, len(a2) / sr):
                word['start'] = round(word['start'] + offset, 3); word['end'] = round(word['end'] + offset, 3)
                ln['word_times'].append(word)
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
