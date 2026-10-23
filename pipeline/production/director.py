"""Deterministic support-plane placement, recorded as explicit storyboard repairs."""
from pipeline.animation.scene import character_scale,actor_pose
from pipeline.models import Prop
def prepare(episode,size):
    changes=[];scale=character_scale(size);h=size[1]
    for scene in episode.scenes:
        for a in scene.actions:
            if a.action not in ('sit','stand','type'):continue
            scale=character_scale(size);world_width=size[0]/scale
            at_start,_=actor_pose(scene,a.actor,a.start,world_width,h/scale)
            x=at_start.joints['hip'][0]/world_width
            if not any(p.kind in ('chair','bench') and abs(p.x-x)<.12 for p in scene.props):
                if len(scene.props)>=12:raise ValueError(scene.id+': no room for required seating prop')
                ident='seat_'+a.actor
                if any(p.id==ident for p in scene.props):ident+='_'+str(len(scene.props))
                scene.props.append(Prop(id=ident,kind='chair',x=max(.05,min(.95,x-.02)),y=.70))
                changes.append({'scene':scene.id,'prop':ident,'reason':'Added aligned seating required by '+str(a.action)})
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
