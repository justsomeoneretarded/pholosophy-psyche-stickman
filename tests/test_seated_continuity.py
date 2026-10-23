import pytest
from pipeline.models import Scene,Action,Episode
from pipeline.animation.scene import actor_pose
from pipeline.production.director import prepare
def test_thinking_preserves_seating_until_explicit_stand():
    s=Scene(id='seated',purpose='Sit and consider the decision',narration='She sits to think, then stands to make a decision.',duration=6,actions=[Action(action='sit',end=1),Action(action='think',start=1,end=4),Action(action='stand',start=4,end=6)])
    thinking,_=actor_pose(s,'main',3)
    standing,_=actor_pose(s,'main',6)
    assert thinking.joints['hip'][1]>-.35
    assert standing.joints['hip'][1]<-.45
    e=Episode(title='A seated thought',thesis='Thoughtful acting should preserve the physical seated state until standing.',metaphor='A chair provides a moment of reflection.',framing='philosophical_exploration',scenes=[s,s.model_copy(deep=True,update={'id':'s2'})])
    assert prepare(e,(1920,1080))
    assert any(p.kind=='chair' for p in e.scenes[0].props)
