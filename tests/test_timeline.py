import pytest
from pipeline.models import Episode,Scene,Action
from pipeline.speech.alignment import align
def test_phrase_anchor_uses_actual_word_time_and_global_offset():
    def scene(id):return Scene(id=id,purpose='An exact phrase directs action',narration='She checked her phone again before starting.',duration=10,actions=[Action(action='use_phone',start=1,end=3,anchor='her phone')])
    e=Episode(title='An anchored action',thesis='Narration timing controls the visual action, rather than random placement.',metaphor='A phone becomes a recurring distraction.',framing='philosophical_exploration',scenes=[scene('s1'),scene('s2')])
    words=[{'word':'She','start':0,'end':.4},{'word':'checked','start':.4,'end':.9},{'word':'her','start':1.8,'end':2.1},{'word':'phone','start':2.1,'end':2.5}]
    timeline,captions=align(e,[4,4],[{'words':words},{'words':words}])
    assert e.scenes[0].actions[0].start==pytest.approx(1.8)
    assert timeline[0]['anchors'][0]['matched']
    assert timeline[1]['start']==pytest.approx(4.18)
    assert captions[1]['start']==pytest.approx(4.18)
def test_missing_anchor_is_reported_and_uses_deterministic_fallback():
    def scene(id):return Scene(id=id,purpose='Anchor fallback',narration='She paused before making the decision.',duration=10,actions=[Action(action='think',start=2,end=4,anchor='not spoken')])
    e=Episode(title='Fallback timing',thesis='Unsupported phrase alignment must be explicitly reported to the editor.',metaphor='A pause before the next decision.',framing='philosophical_exploration',scenes=[scene('s1'),scene('s2')])
    timeline,captions=align(e,[5,5],[{'words':[]},{'words':[]}])
    assert e.scenes[0].actions[0].start==pytest.approx(1)
    assert timeline[0]['anchors'][0]['fallback']=='proportional_scene_timing'
