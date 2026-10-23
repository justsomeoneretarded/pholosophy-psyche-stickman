"""Deterministic support-plane placement, recorded as explicit storyboard repairs."""
from pipeline.animation.scene import character_scale
def prepare(episode,size):
    changes=[];scale=character_scale(size);h=size[1]
    for scene in episode.scenes:
        if scene.environment in ('mindscape','void'):continue
        for p in scene.props:
            if p.kind not in ('phone','box','book','cup','bag'):continue
            surfaces=[q.y-.16 for q in scene.props if q.kind in ('desk','table','computer') and abs(q.x-p.x)<.12]
            support=min(surfaces) if surfaces else .78
            desired=support-.0525*scale/h
            if abs(p.y-desired)>.001:
                changes.append({'scene':scene.id,'prop':p.id,'from_y':p.y,'to_y':desired,'reason':'Rest physical object on the nearest table surface or floor'})
                p.y=desired
    return changes
