"""Sound for a film: synthesized sound effects and ambience, a music bed that follows the
picture's intensity, and a loudness-normalized stereo mix.

python audio/sound.py --cues build/cues.json --music build/music.wav --out build/soundtrack.wav

The music file comes from ACE-Step (see audio/music.py). Without it, a quiet synthesized
piano-and-pad fallback is used so a render never fails, but it is clearly second best.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
RNG = np.random.default_rng(11)


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a=0.005, r=None, curve=4.0):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    tail = np.linspace(0, 1, n - na)
    e[na:] = np.exp(-curve * tail) if r is None else np.maximum(0, 1 - tail) ** r
    return e


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype='low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype='high', fs=SR, output='sos'), x)


def noise(sec):
    return RNG.standard_normal(int(sec * SR))


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def reverb(x, sec=1.6, wet=0.25, tone=4000):
    ir = lp(noise(sec), tone) * np.exp(-np.linspace(0, 6, int(sec * SR)))
    ir /= np.sqrt(np.sum(ir ** 2))
    y = signal.fftconvolve(x, ir)[: len(x) + int(sec * SR)]
    out = np.zeros(len(y))
    out[: len(x)] += x * (1 - wet)
    return out + y * wet


# ---------------- sound effects ----------------
def sfx_notification():
    out = np.zeros(int(.45 * SR))
    for i, f in enumerate([1046.5, 1568]):
        s = t_(.3)
        tone = np.sin(2 * np.pi * f * s) + .25 * np.sin(2 * np.pi * f * 2 * s)
        seg = tone * env(len(s), .002, curve=9)
        st = int(i * .09 * SR)
        out[st:st + len(seg)] += seg
    return norm(reverb(out, .5, .15)) * .7


def sfx_buzz():
    s = t_(.75)
    gate = ((s % .37) < .26).astype(float)
    x = signal.square(2 * np.pi * 160 * s) * .5 + np.sin(2 * np.pi * 80 * s)
    return norm(lp(x * gate, 900) * env(len(s), .01, r=.3)) * .8


def sfx_typing():
    x = hp(noise(.035), 1500) * env(int(.035 * SR), .001, curve=18)
    x += np.sin(2 * np.pi * RNG.uniform(1800, 2600) * t_(.035)) * env(int(.035 * SR), .001, curve=30) * .3
    return norm(x) * .5


def sfx_send():
    s = t_(.28)
    sweep = bp(noise(.28), 900, 5000) * np.sin(np.linspace(0, np.pi, len(s))) ** 2
    pop = np.sin(2 * np.pi * (600 + 900 * s / .28) * s) * env(len(s), .002, curve=14)
    return norm(sweep * .6 + pop) * .6


def sfx_whoosh():
    n = int(.8 * SR)
    x = noise(.8)
    centers = np.linspace(300, 2400, n)
    out = np.zeros(n)
    for i in range(0, n, 2400):
        c = centers[i]
        out[i:i + 2400] = bp(x[i:i + 2400 + 600], c * .6, c * 1.4)[:min(2400, n - i)]
    out *= np.sin(np.linspace(0, np.pi, n)) ** 2
    return norm(lp(out, 6000)) * .55


def sfx_impact():
    s = t_(1.6)
    boom = np.sin(2 * np.pi * (55 * np.exp(-s * 1.5) + 30) * s) * env(len(s), .002, curve=3.5)
    hit = lp(noise(1.6), 1800) * env(len(s), .001, curve=22)
    return norm(reverb(boom + hit * .6, 1.8, .3, 2500)) * .95


def sfx_thud():
    s = t_(.5)
    x = np.sin(2 * np.pi * 70 * np.exp(-s * 6) * s) * env(len(s), .002, curve=10) + lp(noise(.5), 700) * env(len(s), .001, curve=16) * .7
    return norm(x) * .9


def sfx_heartbeat():
    out = np.zeros(int(.9 * SR))
    for st, a in [(0, 1), (.22, .7)]:
        s = t_(.25)
        th = np.sin(2 * np.pi * 52 * s) * env(len(s), .004, curve=12) * a
        i = int(st * SR); out[i:i + len(th)] += th
    return norm(lp(out, 200)) * .9


def sfx_clock():
    return norm(hp(noise(.02), 2500) * env(int(.02 * SR), .0005, curve=25)) * .5


def sfx_alarm():
    s = t_(.18)
    return norm(signal.square(2 * np.pi * 1000 * s) * env(len(s), .003, r=.2) * .5 + np.sin(2 * np.pi * 2000 * s) * .2) * .45


def sfx_door():
    s = t_(1.0)
    f = 180 + 60 * np.sin(2 * np.pi * 2.3 * s) + 40 * RNG.standard_normal(len(s)).cumsum() / len(s)
    creak = bp(signal.sawtooth(2 * np.pi * np.cumsum(f) / SR), 300, 2500) * np.sin(np.linspace(0, np.pi, len(s))) * .5
    latch = np.zeros(len(s)); click = hp(noise(.03), 1200) * env(int(.03 * SR), .0005, curve=20); latch[:len(click)] = click
    return norm(reverb(creak + latch, .9, .2)) * .6


def sfx_footsteps():
    n = int(.12 * SR)
    x = lp(noise(.12), RNG.uniform(500, 900)) * env(n, .002, curve=14)
    x += hp(noise(.12), 3000) * env(n, .001, curve=30) * .15
    return norm(x) * .55


def sfx_breath():
    n = int(1.0 * SR)
    return norm(bp(noise(1.0), 400, 2500) * np.sin(np.linspace(0, np.pi, n)) ** 1.5) * .35


def sfx_drone():
    s = t_(2.2)
    x = sum(signal.sawtooth(2 * np.pi * f * s) for f in (43.65, 44.1, 65.4)) / 3
    x = lp(x, 260) + bp(noise(2.2), 200, 900) * .25
    e = np.sin(np.linspace(0, np.pi, len(s))) ** .8
    return norm(reverb(x * e, 1.6, .35, 1500)) * .8


def sfx_pop():
    s = t_(.12)
    return norm(np.sin(2 * np.pi * (500 + 1500 * np.exp(-s * 40)) * s) * env(len(s), .001, curve=20)) * .5


def sfx_click():
    return norm(bp(noise(.03), 1500, 6000) * env(int(.03 * SR), .0005, curve=28)) * .5


def sfx_chime():
    s = t_(2.0)
    x = sum(np.sin(2 * np.pi * f * s) * np.exp(-s * d) / k for k, (f, d) in enumerate([(1318.5, 2), (1975.5, 2.6), (2637, 3.5), (3951, 5)], 1))
    return norm(reverb(x * env(len(s), .002, curve=2), 1.5, .3)) * .5


def sfx_riser():
    s = t_(2.0)
    x = bp(noise(2.0), 500, 6000) * (s / 2) ** 2 + np.sin(2 * np.pi * (200 + 600 * (s / 2) ** 2) * s) * (s / 2) ** 3 * .4
    return norm(x) * .6


def sfx_crowd():
    s = t_(3.0)
    x = sum(bp(noise(3.0), f, f * 1.6) * (0.6 + 0.4 * np.sin(2 * np.pi * RNG.uniform(2, 5) * s + RNG.uniform(0, 6))) for f in (250, 400, 650, 900))
    return norm(x) * .4


def sfx_blip():
    s = t_(.05)
    f = RNG.uniform(520, 760)
    return norm(np.sin(2 * np.pi * f * s) * env(len(s), .002, curve=14)) * .35


def sfx_scribble():
    n = int(.28 * SR)
    x = bp(noise(.28), 2500, 7000) * (0.5 + 0.5 * np.abs(np.sin(np.linspace(0, RNG.uniform(5, 9) * np.pi, n))))
    return norm(x * np.sin(np.linspace(0, np.pi, n)) ** .5) * .35


def sfx_page():
    n = int(.45 * SR)
    return norm(bp(noise(.45), 1200, 6000) * np.sin(np.linspace(0, np.pi, n)) ** 2) * .45


def sfx_knock():
    out = np.zeros(int(.7 * SR))
    for i in range(3):
        k = sfx_thud()[: int(.12 * SR)] * .8; st = int(i * .2 * SR); out[st:st + len(k)] += k
    return norm(bp(out, 120, 2500)) * .8


SFX = {name[4:]: fn for name, fn in globals().items() if name.startswith('sfx_')}
SFX['rain'] = lambda: norm(hp(noise(1.5), 1500)) * .25
SFX['wind'] = lambda: norm(lp(noise(2.0), 500)) * .3
SFX['rain_heavy'] = lambda: norm(hp(noise(3.0), 900)) * .4


# ---------------- ambience beds ----------------
def bed(kind, sec):
    n = int(sec * SR)
    if kind == 'room':
        x = lp(np.cumsum(noise(sec)) * .02, 180) + lp(noise(sec), 120) * .3
        return norm(x) * .05
    if kind == 'rain':
        x = hp(noise(sec), 1200) * .6 + lp(noise(sec), 400) * .3
        drops = np.zeros(n)
        for i in RNG.integers(0, n - 2000, int(sec * 40)):
            d = hp(noise(.01), 3000) * env(int(.01 * SR), .0005, curve=25) * RNG.uniform(.2, 1)
            drops[i:i + len(d)] += d
        return norm(x + drops * .6) * .22
    if kind == 'rain_in':
        return lp(bed('rain', sec), 1400) * .8
    if kind == 'office':
        s = t_(sec)
        hum = np.sin(2 * np.pi * 120 * s) * .3 + lp(noise(sec), 250) * .6
        keys = np.zeros(n)
        for i in RNG.integers(0, max(1, n - SR), max(1, int(sec * 3))):
            k = sfx_typing() * .25; keys[i:i + len(k)] += k[: n - i]
        return norm(hum) * .035 + keys * .5
    if kind == 'wind':
        s = t_(sec)
        return norm(bp(noise(sec), 150, 900) * (.5 + .5 * np.sin(2 * np.pi * .13 * s) ** 2)) * .16
    if kind == 'city':
        s = t_(sec)
        x = lp(noise(sec), 300) * (.7 + .3 * np.sin(2 * np.pi * .05 * s)) + bp(noise(sec), 600, 1800) * .05
        return norm(x) * .1
    if kind == 'cafe':
        s = t_(sec)
        mur = sum(bp(noise(sec), f, f * 1.5) * (.5 + .5 * np.sin(2 * np.pi * RNG.uniform(1.5, 4) * s + RNG.uniform(0, 6))) for f in (220, 380, 600))
        clinks = np.zeros(n)
        for i in RNG.integers(0, max(1, n - SR), max(1, int(sec / 2.5))):
            c = sfx_chime()[: int(.6 * SR)] * .15; clinks[i:i + len(c)] += c[: n - i]
        return norm(mur) * .07 + clinks
    return np.zeros(n)


# ---------------- fallback music ----------------
def fallback_music(sec):
    """Soft felt-piano chords over a pad. Used only when ACE-Step is unavailable."""
    chords = [[57, 64, 69, 72], [53, 60, 65, 69], [48, 55, 64, 67], [55, 62, 67, 71]]  # Am F C G
    n = int(sec * SR)
    out = np.zeros(n + SR * 10)
    bar = 3.3
    for b in range(int(sec / bar) + 1):
        ch = chords[b % 4]
        for j, note in enumerate(ch):
            f = 440 * 2 ** ((note - 69) / 12)
            s = t_(bar * 1.6)
            tone = sum(np.sin(2 * np.pi * f * h * s) * np.exp(-s * (1.4 + h * .9)) / h ** 1.3 for h in range(1, 6))
            tone *= env(len(s), .006, curve=2.2)
            st = int((b * bar + j * .42) * SR)
            out[st:st + len(tone)] += tone * .25
        s = t_(bar)
        pad = sum(np.sin(2 * np.pi * 440 * 2 ** ((nn - 69) / 12) * s * (1 + d)) for nn in ch[:3] for d in (-.002, .002))
        st = int(b * bar * SR)
        out[st:st + len(s)] += lp(pad, 900) * np.sin(np.linspace(0, np.pi, len(s))) * .03
    return norm(reverb(out[:n], 2.4, .4, 3000)[:n]) * .6


# ---------------- mix ----------------
LEVEL = {'off': 0.0, 'low': .32, 'mid': .58, 'high': .9}


def automation(segments, n):
    g = np.zeros(n)
    for seg in segments:
        a, b = int(seg['start'] * SR), int(seg['end'] * SR)
        g[a:b] = LEVEL.get(seg['level'], .58)
    k = int(.6 * SR)
    return np.convolve(g, np.ones(k) / k, mode='same')


def load_wav(path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float64)
    if x.dtype.kind in 'iu' or np.max(np.abs(x)) > 2:
        x /= 32768.0
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if sr != SR:
        x = signal.resample_poly(x, SR, sr, axis=0)
    return x


def mix(cues_path, music_path, out_path, ffmpeg='ffmpeg'):
    meta = json.loads(Path(cues_path).read_text())
    dur = meta['duration']; n = int((dur + .5) * SR)
    out = np.zeros((n, 2))
    # music
    if music_path and Path(music_path).exists():
        m = load_wav(music_path); source = 'ACE-Step score'
        if len(m) < n:  # loop with a crossfade
            reps = int(np.ceil(n / len(m))) + 1; m = np.concatenate([m] * reps)
        m = m[:n]
    else:
        mono = fallback_music(dur + .5); m = np.stack([mono, mono], 1)[:n]; source = 'synthesized fallback'
    m = m / (np.max(np.abs(m)) or 1) * .8
    g = automation(meta['music'], n)
    # voiceover clips
    voice = np.zeros(n)
    vdir = Path(meta.get('voice_dir') or Path(cues_path).parent / 'voice')
    for c in meta['cues']:
        if c['name'] != 'voice':
            continue
        f = vdir / c['file']
        if not f.exists():
            print(f'missing voice clip {f}'); continue
        v = load_wav(f)[:, 0]
        a = int(c['t'] * SR); L = min(len(v), n - a)
        if L > 0:
            voice[a:a + L] += v[:L]
    has_voice = np.abs(voice) > 1e-4
    # duck the music while the demon speaks or the narrator talks
    duck = np.ones(n)
    for c in meta['cues']:
        if c['name'] == 'drone':
            a = int(c['t'] * SR); duck[a:a + int(1.8 * SR)] = .55
    if has_voice.any():
        k = int(.25 * SR)
        busy = np.convolve(has_voice.astype(float), np.ones(k), mode='same') > 0
        duck[busy] = np.minimum(duck[busy], .38)
    duck = np.convolve(duck, np.ones(int(.3 * SR)) / int(.3 * SR), mode='same')
    fade = np.ones(n); fl = int(1.2 * SR); fade[-fl:] = np.linspace(1, 0, fl); fade[:int(.4 * SR)] = np.linspace(0, 1, int(.4 * SR))
    out += m * (g * duck * fade)[:, None]
    # ambience beds, crossfaded per shot
    beds = {}
    for seg in meta.get('ambience', []):
        kind = seg['kind']
        if kind == 'none':
            continue
        if kind not in beds:
            beds[kind] = bed(kind, dur + 1)
        a, b = int(seg['start'] * SR), min(n, int(seg['end'] * SR))
        x = beds[kind][a:b].copy(); L = len(x); f = min(int(.15 * SR), L // 2)
        if f > 0:
            x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        out[a:a + L, 0] += x; out[a:a + L, 1] += x
    # effects
    cache = {}
    for c in meta['cues']:
        name = c['name']
        if name not in SFX or name == 'voice':
            continue
        if name in ('typing', 'footsteps', 'pop', 'click', 'blip', 'scribble') or name not in cache:
            x = SFX[name]()
            if name not in ('typing', 'footsteps', 'pop', 'click', 'blip', 'scribble'):
                cache[name] = x
        else:
            x = cache[name]
        a = int(max(0, c['t']) * SR); L = min(len(x), n - a)
        if L <= 0:
            continue
        pan = RNG.uniform(-.25, .25) if name in ('footsteps', 'typing') else 0
        vol = c.get('vol', 1) * .8
        out[a:a + L, 0] += x[:L] * vol * (1 - pan)
        out[a:a + L, 1] += x[:L] * vol * (1 + pan)
    if has_voice.any():
        vpeak = np.max(np.abs(voice)) or 1
        out[:, 0] += voice / vpeak * .62; out[:, 1] += voice / vpeak * .62
    out = np.tanh(out * 1.1) * .95
    pre = Path(out_path).with_suffix('.pre.wav')
    wavfile.write(pre, SR, (out * 32767).astype(np.int16))
    # loudness: two-pass EBU R128 to -14 LUFS (YouTube playback level)
    r = subprocess.run([ffmpeg, '-hide_banner', '-nostats', '-i', str(pre), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    s = r.stderr; js = json.loads(s[s.rindex('{'):s.rindex('}') + 1])
    flt = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
           f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run([ffmpeg, '-y', '-v', 'error', '-i', str(pre), '-af', flt, '-ar', str(SR), str(out_path)], check=True)
    pre.unlink()
    print(f'soundtrack: {out_path}  music={source}  cues={len(meta["cues"])}')
    return source


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cues', required=True); ap.add_argument('--music'); ap.add_argument('--out', required=True)
    ap.add_argument('--ffmpeg', default='ffmpeg')
    a = ap.parse_args()
    mix(a.cues, a.music, a.out, a.ffmpeg)
