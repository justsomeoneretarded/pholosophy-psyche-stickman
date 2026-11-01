"""Speech retries must be verified, and secondary spoken parts cannot be skipped."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('studio_voice',Path('audio/voice.py'))
voice=importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)

def test_twist_is_verified_even_when_main_line_is_good(monkeypatch):
    def transcribe(path,expected,whisper):
        return (.98 if str(path)=='main.wav' else .25),[]
    monkeypatch.setattr(voice,'verify',transcribe)
    takes=[(0,0,{'text':'The main explanation.','twist':'An important final distinction.'},Path('main.wav'),Path('twist.wav'))]
    records=voice.verify_takes(takes,None)
    assert len(records)==2
    assert records[0]['passed']
    assert not records[1]['passed']
    assert records[1]['part']=='twist'

def test_fresh_verification_reflects_regenerated_take(monkeypatch):
    scores=iter([.3,.97])
    monkeypatch.setattr(voice,'verify',lambda *args:(next(scores),[]))
    takes=[(0,0,{'text':'The intended sentence.'},Path('take.wav'),None)]
    assert not voice.verify_takes(takes,None)[0]['passed']
    assert voice.verify_takes(takes,None)[0]['passed']
