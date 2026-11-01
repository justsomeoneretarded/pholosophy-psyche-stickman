from pathlib import Path
import audio.voice as voice
def test_independent_transcription_can_resolve_a_base_model_false_rejection(monkeypatch):
    original={'file':'take.wav','expected':'Heartbreak fades, but its lessons linger like a soft echo.',
              'agreement':.7619,'words':[{'word':'fates'}],'passed':False,'negation_changed':False}
    correct=[{'word':w} for w in original['expected'].split()]
    monkeypatch.setattr(voice,'verify',lambda *args:(1.,correct))
    result=voice.verify_disputed([original],object())[0]
    assert result['passed'] and result['accepted_asr']=='small.en'
    assert result['primary_asr']['agreement']==.7619
def test_second_opinion_does_not_accept_a_missing_negation(monkeypatch):
    record={'file':'take.wav','expected':'It is not certain.','agreement':.7,'words':[],'passed':False,'negation_changed':True}
    monkeypatch.setattr(voice,'verify',lambda *args:(.9,[{'word':w} for w in 'It is certain.'.split()]))
    assert not voice.verify_disputed([record],object())[0]['passed']
