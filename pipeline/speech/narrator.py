"""Narration with Chatterbox Turbo on CPU, cloned from a bundled narrator reference.

Adapted from the Top10-Movies pipeline: sentence-by-sentence generation, best of
two takes per sentence, a broadcast voice chain, and faster-whisper verification.
Narrators: warguy (default), kit-laser, female  (assets/voices/<name>.ogg).
"""
import gc
import hashlib
import json
import os
import re
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOICES = {'warguy': 'warguy.ogg', 'kit-laser': 'kit-laser.ogg', 'kit_laser': 'kit-laser.ogg', 'female': 'female.ogg'}

# Philosophy pacing: longer breaths than a countdown video.
SENTENCE_GAPS = {'?': .62, '!': .45, '.': .42, ':': .4, ';': .32, ',': .2}
# Delivery -> original Chatterbox emotion settings (exaggeration, cfg_weight, temperature); calm/normal use Turbo.
EMOTION = {'dramatic': (.58, .32, .75)}
VOICE_CHAIN = ('asetpts=PTS-STARTPTS,highpass=f=70,'
               'agate=threshold=0.001:ratio=1.5:range=0.25:attack=5:release=180:knee=4,'
               'deesser=i=0.35:m=0.5:f=0.5:s=o,'
               'acompressor=threshold=-21dB:ratio=3:attack=8:release=140:makeup=3:knee=4,'
               'equalizer=f=140:t=q:w=0.9:g=2.5,equalizer=f=3000:t=q:w=0.8:g=1.5,highshelf=f=10000:g=1,'
               'atempo={tempo},asoftclip=type=tanh:threshold=0.95,apad=pad_dur=0.2,loudnorm=I=-18:TP=-2:LRA=9')
PRONUNCIATIONS = {r'\bNietzsche\b': 'Neecha', r'\bCamus\b': 'Camoo', r'\bSartre\b': 'Sartruh', r'\bKierkegaard\b': 'Kirkegard',
                  r'\bSisyphus\b': 'Sisifus', r'\bDescartes\b': 'Day-cart', r'\bJung\b': 'Yoong', r'\bFreud\b': 'Froyd',
                  r'\bSchopenhauer\b': 'Shopenhower', r'\bHeidegger\b': 'Hyde-egger', r'\bEpictetus\b': 'Epic-tee-tus',
                  r'\bSeneca\b': 'Senneka', r'\bZhuangzi\b': 'Jwahng-dzuh', r'&': ' and '}


def reference(name):
    key = (name or 'warguy').strip().lower().replace(' ', '-')
    path = ROOT / 'assets' / 'voices' / VOICES.get(key, 'warguy.ogg')
    if not path.exists():
        raise FileNotFoundError(f'Narrator reference missing: {path}')
    return path


def spoken(text):
    for pattern, replacement in PRONUNCIATIONS.items():
        text = re.sub(pattern, replacement, text)
    return ' '.join(text.split())


def sentences(text):
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])', text) if p.strip()]
    merged = []
    for p in parts:
        if merged and len(p.split()) < 3:
            merged[-1] += ' ' + p
        else:
            merged.append(p)
    return merged or [text]


def take_score(samples, rate, words):
    import numpy as np
    if samples.size < rate * .3:
        return float('-inf')
    frame = max(1, rate // 50)
    usable = samples[: samples.size // frame * frame].reshape(-1, frame)
    energy = 20 * np.log10(np.sqrt((usable ** 2).mean(axis=1)) + 1e-6)
    voiced = energy > energy.max() - 35
    first, last = (np.argmax(voiced), len(voiced) - np.argmax(voiced[::-1])) if voiced.any() else (0, len(voiced))
    longest = run = 0
    for silent in ~voiced[first:last]:
        run = run + 1 if silent else 0
        longest = max(longest, run)
    seconds = (last - first) / 50
    wpm = words * 60 / max(.3, seconds)
    return -abs(wpm - 150) / 25 - max(0, longest / 50 - .7) * 3


def wav_seconds(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out or 0)


class Narrator:
    def __init__(self, name='warguy'):
        import torch
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        torch.set_num_threads(int(os.getenv('TTS_THREADS', str(os.cpu_count() or 4))))
        self.model_name = os.getenv('TTS_MODEL', 'turbo')
        self.reference = reference(name)
        self.model = ChatterboxTurboTTS.from_pretrained(device='cpu', nano=self.model_name == 'nano')
        self.model.prepare_conditionals(str(self.reference))
        self.emotional = None
        self.takes = max(1, min(3, int(os.getenv('VOICE_TAKES', '2'))))
        self.tempo = float(os.getenv('VOICE_TEMPO', '0.96'))

    def _emotional_model(self):
        if self.emotional is None:
            try:
                from chatterbox.tts import ChatterboxTTS
                self.emotional = ChatterboxTTS.from_pretrained(device='cpu')
                self.emotional.prepare_conditionals(str(self.reference), exaggeration=.55)
            except Exception as exc:  # noqa: BLE001 -- Turbo still voices every line
                print(f'Expressive model unavailable ({type(exc).__name__}); Turbo voices every line.', flush=True)
                self.emotional = False
        return self.emotional or None

    def _generate(self, text, delivery, seed):
        import torch
        torch.manual_seed(seed)
        settings = EMOTION.get(delivery)
        model = self._emotional_model() if settings else None
        with torch.inference_mode():
            if model is not None:
                ex, cfg, temp = settings
                wav = model.generate(text, exaggeration=ex, cfg_weight=cfg, temperature=temp)
                return wav.squeeze().detach().cpu().numpy(), model.sr
            wav = self.model.generate(text)
            return wav.squeeze().detach().cpu().numpy(), self.model.sr

    @staticmethod
    def _trim(samples, rate):
        import numpy as np
        loud = np.flatnonzero(np.abs(samples) > max(1e-4, float(np.abs(samples).max()) * .02))
        if not loud.size:
            return samples[:0]
        m = int(rate * .04)
        return samples[max(0, loud[0] - m): min(samples.size, loud[-1] + m)]

    def speak(self, text, output, delivery='calm', seed=0):
        import numpy as np
        import soundfile as sf
        output = Path(output)
        for attempt in range(3):
            pieces, rate = [], None
            base = int(hashlib.sha1(text.encode()).hexdigest()[:8], 16) + seed * 7919 + attempt * 104729
            try:
                for i, sentence in enumerate(sentences(spoken(text))):
                    best, best_score = None, float('-inf')
                    for take in range(1 if delivery in EMOTION else self.takes):
                        samples, rate = self._generate(sentence, delivery, base + i * 131 + take * 17)
                        if not np.isfinite(samples).all() or not samples.size or np.max(np.abs(samples)) < 1e-5:
                            continue
                        samples = self._trim(samples.astype(np.float32), rate)
                        score = take_score(samples, rate, len(sentence.split()))
                        if score > best_score:
                            best, best_score = samples, score
                    if best is None:
                        raise ValueError('silent take')
                    gap = SENTENCE_GAPS.get(sentence.rstrip('"\')')[-1:], .42)
                    pieces += [best, np.zeros(int(rate * gap), dtype=np.float32)]
            except (ValueError, RuntimeError) as exc:
                print(f'Voice attempt {attempt + 1}: unusable take ({exc}); retrying.', flush=True)
                continue
            samples = np.concatenate(pieces[:-1]) if len(pieces) > 1 else pieces[0]
            raw = output.with_suffix('.raw.wav')
            sf.write(raw, samples, rate, subtype='PCM_24')
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(raw), '-af', VOICE_CHAIN.format(tempo=self.tempo),
                            '-ar', '48000', '-ac', '1', str(output)], check=True)
            raw.unlink(missing_ok=True)
            seconds = wav_seconds(output)
            if .5 <= seconds <= len(text.split()) * 1.2 + 10:
                return seconds
            output.unlink(missing_ok=True)
        raise RuntimeError('Voice generation failed after three attempts')

    def close(self):
        del self.model
        self.emotional = None
        gc.collect()


def verify(path, expected, whisper):
    """Transcribe and compare with the script; returns (agreement, words with timings)."""
    from difflib import SequenceMatcher
    import numpy as np
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', '16000', 'pipe:1'])
    audio = np.frombuffer(raw, dtype='<f4').copy()
    segments, _ = whisper.transcribe(audio, language='en', word_timestamps=True, beam_size=5, vad_filter=True,
                                     condition_on_previous_text=False)
    words = [{'word': w.word.strip(), 'start': w.start, 'end': w.end} for s in segments for w in (s.words or [])]
    tok = lambda t: re.findall(r'[a-z0-9]+', t.lower())
    agreement = SequenceMatcher(None, tok(spoken(expected)), tok(' '.join(w['word'] for w in words)), autojunk=False).ratio()
    return agreement, words


def voice_episode(episode, out_dir, narrator='warguy', whisper_model='base.en'):
    """Speak every narrated beat; returns {scene_id: {file, seconds, words, agreement}}."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'speech.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    voice = None
    pending = [s for s in episode.scenes if s.voiced]
    for i, scene in enumerate(pending):
        signature = hashlib.sha1(json.dumps([scene.narration, narrator, scene.delivery]).encode()).hexdigest()[:16]
        entry = manifest.get(scene.id)
        if entry and entry.get('signature') == signature and (out / entry['file']).exists():
            continue
        if voice is None:
            voice = Narrator(narrator)
        path = out / f'{scene.id}.wav'
        print(f'Narrating {scene.id} ({i + 1}/{len(pending)}, {len(scene.narration.split())} words, {scene.delivery})', flush=True)
        seconds = voice.speak(scene.narration, path, scene.delivery)
        manifest[scene.id] = {'file': path.name, 'seconds': seconds, 'signature': signature, 'delivery': scene.delivery}
        manifest_path.write_text(json.dumps(manifest, indent=2))
    if voice is not None:
        voice.close()
    from faster_whisper import WhisperModel
    whisper = WhisperModel(whisper_model, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1)
    redo = []
    for scene in pending:
        entry = manifest[scene.id]
        agreement, words = verify(out / entry['file'], scene.narration, whisper)
        entry.update(agreement=agreement, words=words)
        print(f'{scene.id}: speech agreement {agreement:.2f}', flush=True)
        if agreement < .8:
            redo.append(scene)
    if redo:
        del whisper
        voice = Narrator(narrator)
        for scene in redo:
            entry = manifest[scene.id]
            entry['seconds'] = voice.speak(scene.narration, out / entry['file'], scene.delivery, seed=3)
        voice.close()
        from faster_whisper import WhisperModel as W
        whisper = W(whisper_model, device='cpu', compute_type='int8', cpu_threads=4, num_workers=1)
        for scene in redo:
            entry = manifest[scene.id]
            agreement, words = verify(out / entry['file'], scene.narration, whisper)
            entry.update(agreement=agreement, words=words)
            if agreement < .7:
                print(f'::warning title=Narration check::{scene.id} agreement {agreement:.2f} after retry; keeping the best take', flush=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest
