import pytest
from pipeline.models import Scene,Action
from pipeline.animation.scene import actor_pose
def test_finished_walk_settles_and_next_gesture_stays_at_destination():
    s=Scene(id='continuity',purpose='Walk then think at the reached position',narration='He takes a short walk and pauses to reconsider.',duration=5,actions=[Action(action='walk',start=0,end=1,x=.35),Action(action='think',start=3,end=5,x=.35)])
    settled,_=actor_pose(s,'main',2)
    thinking,_=actor_pose(s,'main',4)
    assert settled.joints['left_foot'][1]==pytest.approx(0,abs=.005)
    assert settled.joints['right_foot'][1]==pytest.approx(0,abs=.005)
    assert thinking.joints['hip'][0]==pytest.approx(settled.joints['hip'][0],abs=.01)
