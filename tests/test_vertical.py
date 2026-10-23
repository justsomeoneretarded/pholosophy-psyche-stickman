from pipeline.animation.scene import character_scale,frame
from pipeline.models import Scene,Action
from pipeline.production.quality import motion_checks
def test_portrait_has_its_own_character_framing():
    scale=character_scale((1080,1920))
    assert scale/1920>.30
    s=Scene(id='portrait',purpose='Portrait framing',narration='A character considers one small decision.',duration=2,actions=[Action(action='think',end=2,x=.45)],symbol='thought')
    assert frame(s,1,(1080,1920)).size==(1080,1920)
def test_frame_exit_qa_uses_the_actual_canvas_geometry():
    from pipeline.models import Episode
    s=Scene(id='wide',purpose='Test travel distance',narration='A character runs across the stage.',duration=2,actions=[Action(action='sprint',end=2,x=.55)])
    e=Episode(title='Travel in portrait',thesis='Frame safety depends on actual character scale and canvas width.',metaphor='A stage with a changing aspect ratio.',framing='philosophical_exploration',scenes=[s,s.model_copy(update={'id':'other'})])
    assert not motion_checks(e,(1080,1920))['passed']
