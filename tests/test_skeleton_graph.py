from pipeline.animation.rig import pose,BONES
def test_every_joint_is_connected_to_the_pelvis():
    joints=pose('wave',.5,2).joints
    reachable={'hip'}
    while True:
        expanded=reachable|{b for a,b in BONES if a in reachable}|{a for a,b in BONES if b in reachable}
        if expanded==reachable:break
        reachable=expanded
    assert set(joints)<=reachable
