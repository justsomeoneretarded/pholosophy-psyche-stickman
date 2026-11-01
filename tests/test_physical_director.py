import json,subprocess
from pathlib import Path
from story.director import direct_beat,enrich_film
V=json.loads(Path('engine/vocab.json').read_text())
def test_physical_directions_preserve_action_order_and_actor():
    b={'who':['alex','sam'],'where':'cafe','seconds':12,'what_happens':'Alex draws a seedling. Sam shows the sketch.'}
    shots=direct_beat(b,V)
    assert shots[0]['actors'][0]['pose']=='write'
    assert shots[0]['actors'][0]['hold']=='pencil'
    assert shots[0]['actors'][1]['pose']=='show'
def test_recut_preserves_recorded_speech_and_duration():
    f={'shots':[{'beat':1,'dur':7.2,'actors':[{'id':'alex','pose':'sit','x':19}], 'lines':[{'who':'narrator','text':'A sketch can matter to one person.','voice_file':'x.wav','word_times':[{'start':0,'end':1,'word':'A'}]}]}]}
    before=json.dumps(f['shots'][0]['lines'])
    enrich_film(f,{'beats':[{'what_happens':'Alex draws a seedling.'}]})
    assert f['shots'][0]['dur']==7.2
    assert json.dumps(f['shots'][0]['lines'])==before
    assert f['shots'][0]['actors'][0]['pose']=='write'
def test_abstract_words_do_not_trigger_unrelated_motion():
    assert direct_beat({'who':['alex'],'where':'park','what_happens':'The drawing is a memory of childhood.'},V)[0]['actors'][0]['pose'] in {'stand','sit'}

def test_recipient_does_not_copy_the_givers_action():
    s=direct_beat({'who':['alex','sam'],'where':'cafe','what_happens':'Alex shows sketch to Sam.'},V)[0]
    assert s['actors'][0]['pose']=='show'
    assert s['actors'][1]['pose'] in {'sit','stand'}
