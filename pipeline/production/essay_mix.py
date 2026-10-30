"""Timeline, narration track, music bed, sound design and final mix for noir essays."""
import json
import math
import re
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RATE = 48000
LEAD, TAIL = .5, .85          # silence before and after narration inside a narrated beat


def decode(path, rate=RATE, channels=1):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', str(channels), '-ar', str(rate), 'pipe:1'])
    data = np.frombuffer(raw, dtype='<f4').copy()
    return data.reshape(-1, channels) if channels > 1 else data


def write_wav(path, samples, rate=RATE):
    import wave
    data = (np.clip(samples, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- timeline
def build_timeline(episode, speech):
    """Fit every beat to its narration (or keep the silent beat length) and rescale its staging."""
    timeline, captions, cursor = [], [], 0.
    for scene in episode.scenes:
        entry = speech.get(scene.id) if scene.voiced else None
        old = scene.duration
        new = (LEAD + entry['seconds'] + TAIL) if entry else old
        scene.duration = round(new, 3)
        k = new / old if old else 1
        for a in scene.actions:
            a.start = round(a.start * k, 3)
            a.end = round(max(a.start + .2, a.end * k), 3)
        if entry:
            captions += script_captions(scene.narration, entry.get('words', []), cursor + LEAD, entry['seconds'])
        timeline.append({'scene_id': scene.id, 'start': round(cursor, 3), 'end': round(cursor + new, 3), 'voiced': bool(entry),
                         'setpiece': scene.setpiece, 'amber': scene.amber, 'text': scene.text})
        cursor += new
    return timeline, captions


def script_captions(text, words, offset, seconds, max_chars=46):
    """Captions with the exact script words, timed from the speech recogniser."""
    script = text.split()
    if not script:
        return []
    times = []
    for i in range(len(script)):
        if words:
            w = words[min(len(words) - 1, int(i * len(words) / len(script)))]
            times.append((w['start'], w['end']))
        else:
            times.append((seconds * i / len(script), seconds * (i + 1) / len(script)))
    out, chunk, start = [], [], None
    for i, word in enumerate(script):
        if start is None:
            start = times[i][0]
        chunk.append(word)
        end_sentence = word[-1:] in '.?!;:'
        if len(' '.join(chunk)) >= max_chars or end_sentence or i == len(script) - 1:
            out.append({'start': round(offset + start, 3), 'end': round(offset + max(times[i][1], start + .6), 3), 'text': ' '.join(chunk)})
            chunk, start = [], None
    return out


# ---------------------------------------------------------------- narration
def narration_track(timeline, speech, speech_dir, total):
    track = np.zeros(int(total * RATE) + RATE, dtype=np.float32)
    for row in timeline:
        entry = speech.get(row['scene_id']) if row['voiced'] else None
        if not entry:
            continue
        voice = decode(Path(speech_dir) / entry['file'])
        at = int((row['start'] + LEAD) * RATE)
        track[at:at + voice.size] += voice[: max(0, track.size - at)]
    return track


# ---------------------------------------------------------------- music
def bundled_track(mood):
    catalog = json.loads((ROOT / 'assets' / 'music' / 'catalog.json').read_text())
    name = 'aurora' if mood == 'hopeful' else 'celestial'
    return ROOT / 'assets' / 'music' / catalog[name]['file'], catalog[name]


def looped(samples, length, fade=3.):
    """Repeat a cue to `length` samples with equal-power crossfades."""
    f = int(fade * RATE)
    if samples.size >= length:
        return samples[:length].copy()
    out = samples.copy()
    curve = np.linspace(0, 1, f, dtype=np.float32)
    while out.size < length:
        head = samples[:f] * np.sqrt(curve)
        out[-f:] = out[-f:] * np.sqrt(1 - curve) + head
        out = np.concatenate([out, samples[f:]])
    return out[:length]


def music_bed(timeline, total, scores, credits):
    """Contemplative score throughout, hopeful score under amber beats; louder in silent beats."""
    n = int(total * RATE) + RATE
    cues = {}
    for mood in ('contemplative', 'hopeful'):
        path = scores.get(mood)
        if path and Path(path).exists():
            cues[mood] = decode(path)
            credits.append({'music': f'Original score ({mood}), generated with ACE-Step 1.5 (MIT)'})
        else:
            p, meta = bundled_track(mood)
            cues[mood] = decode(p)
            credits.append({'music': f'"{meta["title"]}" by {meta["artist"]}, {meta["license"]} ({meta["source"]})'})
    for mood in cues:
        peak = float(np.percentile(np.abs(cues[mood]), 99.5)) or 1.
        cues[mood] = cues[mood] / peak * .5
    base = looped(cues['contemplative'], n)
    hope = looped(cues['hopeful'], n)
    # Envelopes at 100 Hz, smoothed, then stretched to audio rate (fast).
    env_rate = 100
    m = int(n / RATE * env_rate) + 2
    w_env, l_env = np.zeros(m, dtype=np.float32), np.zeros(m, dtype=np.float32)
    for row in timeline:
        a, b = int(row['start'] * env_rate), int(row['end'] * env_rate)
        w_env[a:b] = 1. if row['amber'] else 0.
        l_env[a:b] = .95 if not row['voiced'] else .3
    kernel = np.hanning(int(1.6 * env_rate)).astype(np.float32)
    kernel /= kernel.sum()
    w_env, l_env = np.convolve(w_env, kernel, mode='same'), np.convolve(l_env, kernel, mode='same')
    grid = np.arange(n) / RATE * env_rate
    mix_w = np.interp(grid, np.arange(m), w_env).astype(np.float32)
    level = np.interp(grid, np.arange(m), l_env).astype(np.float32)
    bed = (base * np.sqrt(1 - mix_w) + hope * np.sqrt(mix_w)) * level
    fade_in, fade_out = int(2 * RATE), int(4 * RATE)
    bed[:fade_in] *= np.linspace(0, 1, fade_in)
    end = int(total * RATE)
    bed[max(0, end - fade_out):end] *= np.linspace(1, 0, min(fade_out, end))
    bed[end:] = 0
    return bed


# ---------------------------------------------------------------- sound design
def _noise(rng, n):
    return rng.normal(0, 1, n).astype(np.float32)


def sound(kind, rng):
    t = lambda s: np.arange(int(s * RATE)) / RATE
    if kind == 'whoosh':
        x = t(1.2)
        return .05 * _noise(rng, x.size) * np.sin(np.pi * x / 1.2) ** 2
    if kind == 'crumble':
        x = t(1.4)
        grains = _noise(rng, x.size) * (rng.random(x.size) > .985) * 3
        return (.06 * grains + .03 * _noise(rng, x.size)) * np.exp(-x * 2.2)
    if kind == 'crack':
        x = t(2.5)
        return (.16 * _noise(rng, x.size) * np.exp(-x * 9) + .12 * np.sin(2 * np.pi * 48 * x) * np.exp(-x * 1.8))
    if kind == 'wind':
        x = t(6)
        n = np.convolve(_noise(rng, x.size), np.ones(60) / 60, mode='same')
        return .5 * n * np.sin(np.pi * x / 6) * (.6 + .4 * np.sin(x * .9))
    if kind == 'chime':
        x = t(3)
        return sum(.03 * np.sin(2 * np.pi * f * x) * np.exp(-x * 1.4) for f in (523.25, 659.25, 783.99))
    if kind == 'rumble':
        x = t(3)
        return .1 * np.convolve(_noise(rng, x.size), np.ones(400) / 400, mode='same') * 8 * np.exp(-x * .6)
    if kind == 'clink':
        x = t(.4)
        return .04 * np.sin(2 * np.pi * 2100 * x) * np.exp(-x * 25)
    if kind == 'heartbeat':
        x = t(1)
        return .12 * np.sin(2 * np.pi * 52 * x) * (np.exp(-((x - .05) * 30) ** 2) + .7 * np.exp(-((x - .3) * 30) ** 2))
    if kind == 'tick':
        x = t(.08)
        return .05 * np.sin(2 * np.pi * 1800 * x) * np.exp(-x * 80)
    if kind == 'step':
        x = t(.25)
        return .045 * np.sin(2 * np.pi * 90 * x) * np.exp(-x * 45) + .01 * _noise(rng, x.size) * np.exp(-x * 70)
    return np.zeros(1, dtype=np.float32)


def setpiece_sounds(row, labels_count, rng):
    """(time offset, kind) events for a beat, matched to what the set piece shows."""
    a, d = row['start'], row['end'] - row['start']
    sp = row['setpiece']
    ev = [(a, 'whoosh')]
    if sp == 'word_wall':
        n = max(1, labels_count or 4)
        ev += [(a + d * (.22 + i * .5 / max(1, n - 1)), 'crumble') for i in range(n)]
    elif sp == 'pillar':
        ev += [(a + d * .38 - .7, 'rumble'), (a + d * .38, 'crack')]
    elif sp in ('fall', 'desert'):
        ev += [(a + k * 5.5, 'wind') for k in range(int(d / 5.5) + 1)]
    elif sp in ('chalk_door', 'flower', 'doors') or row['amber']:
        ev += [(a + d * (.6 if sp == 'chalk_door' else .55), 'chime')]
    elif sp == 'sisyphus':
        ev += [(a + d * .76, 'rumble')]
    elif sp == 'chains':
        ev += [(a + d * k / 12, 'clink') for k in range(12)]
    elif sp in ('clock', 'routine_loop'):
        ev += [(a + k * .5, 'tick') for k in range(int(d / .5))]
    elif sp in ('giant_hand', 'shadow_companion', 'mirror', 'cage'):
        ev += [(a + d * .3 + k * 1.1, 'heartbeat') for k in range(3)]
    return ev


def effects_track(timeline, episode, total, seed=5):
    rng = np.random.default_rng(seed)
    track = np.zeros(int(total * RATE) + RATE * 7, dtype=np.float32)
    scenes = {s.id: s for s in episode.scenes}
    for row in timeline:
        for at, kind in setpiece_sounds(row, len(scenes[row['scene_id']].labels), rng):
            snd = sound(kind, rng).astype(np.float32)
            i = int(max(0, at) * RATE)
            track[i:i + snd.size] += snd[: max(0, track.size - i)]
    return track[: int(total * RATE) + RATE]


def mix(out, timeline, episode, speech, speech_dir, scores):
    total = timeline[-1]['end']
    credits = []
    voice = narration_track(timeline, speech, speech_dir, total)
    music = music_bed(timeline, total, scores, credits)
    fx = effects_track(timeline, episode, total)
    n = min(voice.size, music.size, fx.size)
    out = Path(out)
    write_wav(out / 'narration.wav', voice[:n])
    write_wav(out / 'music_bed.wav', music[:n])
    write_wav(out / 'effects.wav', fx[:n])
    graph = ('[1:a]volume=0.9[m];[0:a]asplit=2[v][key];[m][key]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=600[duck];'
             '[v][duck][2:a]amix=inputs=3:normalize=0[a]')
    inputs = ['-i', str(out / 'narration.wav'), '-i', str(out / 'music_bed.wav'), '-i', str(out / 'effects.wav')]
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', graph, '-map', '[a]', '-t', f'{total:.3f}',
                    '-ar', '48000', '-c:a', 'pcm_s24le', str(out / 'premix.wav')], check=True)
    # Two-pass loudness normalisation to YouTube's -14 LUFS, -1 dBTP.
    measure = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(out / 'premix.wav'), '-af',
                              'loudnorm=I=-14:TP=-1:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(measure[measure.rfind('{'):measure.rfind('}') + 1])
    second = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
              f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(out / 'premix.wav'), '-af', second, '-ar', '48000', '-c:a', 'pcm_s16le',
                    str(out / 'final_mix.wav')], check=True)
    return credits
