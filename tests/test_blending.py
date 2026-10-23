import math
import numpy as np
from pipeline.models import Scene,Action
from pipeline.animation.scene import actor_pose
def test_seated_typing_to_raised_arm_has_no_ik_branch_snap():
    s=Scene(id='blend',purpose='Stand and celebrate',narration='After finishing the draft, he stands and celebrates the small beginning.',duration=4,actions=[Action(action='type',end=2),Action(action='celebrate',start=2,end=4)])
    samples=[actor_pose(s,'main',float(t))[0].joints for t in np.arange(1.9,2.6,1/30)]
    assert max(math.dist(a[k],b[k]) for a,b in zip(samples,samples[1:]) for k in a)<.20
def test_handshake_arrival_blends_out_of_walk_cycle():
    s=Scene(id='shake',purpose='Meet a friend',narration='The two friends approach each other and shake hands.',duration=4,characters=['main','friend'],actions=[Action(action='handshake',end=4,x=.35),Action(actor='friend',action='handshake',end=4,x=.65)])
    ww=1920/(1080*.49)
    for actor in s.characters:
        samples=[actor_pose(s,actor,float(t),ww,1080/(1080*.49))[0].joints for t in np.arange(.7,2.,1/30)]
        assert max(math.dist(a[k],b[k]) for a,b in zip(samples,samples[1:]) for k in a)<.20
