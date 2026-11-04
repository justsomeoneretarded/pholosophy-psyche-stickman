"""Data-only physical staging validated against the actual production rig vocabulary."""
from __future__ import annotations
import copy,json,math
from pathlib import Path
VOCAB=json.loads((Path(__file__).resolve().parents[1]/'engine/vocab.json').read_text())
FIELDS={'actors','camera','phone','insert','items','sfx','lines','door','door_at','big','set','scene','transition'}
def staging_contract():
    return {'poses':VOCAB['poses'],'holds':VOCAB['holds'],'moods':VOCAB['moods'],
            'frames':VOCAB['frames'],'sets':list(VOCAB['sets']),'scene':VOCAB['scene'],
            'phase_fields':sorted(FIELDS),
            'actor_example':{'id':'existing_cast_id','pose':'write','x':50,'hold':'pencil'},
            'rules':'Use existing cast IDs; x/to are 0-100. Use write for drawing/painting, not paint. Supported held props only. Narration stays in the beat. Do not invent beat-level action fields.'}

def validate_scene(scene):
    if not isinstance(scene,dict):raise ValueError('A composed scene needs a scene object')
    if scene.get('base') not in VOCAB['scene']['base']:
        raise ValueError('Unsupported scene base: '+str(scene.get('base'))+'; choose '+', '.join(VOCAB['scene']['base'])+'; named sets belong in where/set')
    for key in ('wall','ground','backdrop','light'):
        if key in scene and scene[key] not in VOCAB['scene'][key]:
            raise ValueError('Unsupported scene '+key+': '+str(scene[key]))
    elements=scene.get('elements',[])
    if not isinstance(elements,list):raise ValueError('Scene elements must be a list')
    for element in elements:
        if not isinstance(element,dict) or element.get('type') not in VOCAB['scene']['elements']:
            raise ValueError('Unsupported scene element: '+str(element))
        x=element.get('x',50)
        if type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=100:
            raise ValueError('Scene element x must be finite and between 0 and 100')

def validate_staging(beat,cast):
    phases=beat.get('staging')
    if phases is None:return
    if not isinstance(phases,list) or not 1<=len(phases)<=8:raise ValueError('staging needs 1-8 physical phases')
    known={p['id'] for p in cast}
    for phase in phases:
        if not isinstance(phase,dict) or set(phase)-FIELDS:raise ValueError('Unknown staging fields; use actors, camera and supported shot data')
        if 'scene' in phase:validate_scene(phase['scene'])
        actors=phase.get('actors') or []
        if not isinstance(actors,list) or len(actors)>5:raise ValueError('A staging phase supports up to five actors')
        present={a.get('id') for a in actors if isinstance(a,dict)}
        if len(present)!=len(actors):raise ValueError('Actor IDs must be unique within a phase')
        for actor in actors:
            if actor.get('id') not in known:raise ValueError('Staging refers to an unknown cast ID')
            if actor.get('pose') not in VOCAB['poses']:raise ValueError('Unsupported rig pose: '+str(actor.get('pose'))+'; choose one of '+', '.join(VOCAB['poses']))
            for key in ('x','to'):
                if key in actor and (type(actor[key]) not in (int,float) or not math.isfinite(actor[key]) or not 0<=actor[key]<=100):
                    raise ValueError('Staging '+key+' must be a finite coordinate from 0 to 100')
            if actor.get('target') and actor['target'] not in present:raise ValueError('An interaction target must appear in the same staging phase')
            if actor.get('hold') and actor['hold'] not in VOCAB['holds']:raise ValueError('Unsupported held prop: '+str(actor['hold'])+'; choose one of '+', '.join(VOCAB['holds']))
            if actor.get('mood') and actor['mood'] not in VOCAB['moods']:raise ValueError('Unsupported facial mood')
        camera=phase.get('camera') or {}
        frame=camera.get('frame','wide')
        if frame not in VOCAB['frames']:raise ValueError('Unsupported camera frame')
        if camera.get('on') and camera['on'] not in present:raise ValueError('Camera target is absent')
        if frame=='phone' and not isinstance(phase.get('phone'),dict):raise ValueError('A phone shot needs phone screen data')
        if frame=='insert' and not isinstance(phase.get('insert'),dict):raise ValueError('An insert shot needs insert data')
        if not actors and frame not in ('phone','insert'):raise ValueError('Staging needs visible actors or a supported object shot')
        if phase.get('set') and phase['set'] not in VOCAB['sets']:raise ValueError('Unsupported staging set')
        if any(line.get('who')=='narrator' for line in phase.get('lines',[])):raise ValueError('Keep narration in the beat; do not duplicate it in staging')
def compile_staging(beat):
    phases=beat.get('staging')
    if not phases:return None
    base={k:copy.deepcopy(beat[k]) for k in ('time','weather','grade','scene') if beat.get(k)}
    base['set']=beat.get('where','void')
    result=[]
    for phase in phases:
        shot={**copy.deepcopy(base),**copy.deepcopy(phase),'dur':max(3,float(beat.get('seconds',10))/len(phases)),
              '_directed':True,'acting_source':'validated model staging'}
        actors=shot.get('actors',[])
        shot.setdefault('camera',{'frame':'two' if len(actors)>1 else 'medium','on':actors[0]['id'] if actors else None})
        shot.setdefault('lines',[])
        result.append(shot)
    if result and not any(s['lines'] for s in result):
        result[0]['lines']=copy.deepcopy(beat.get('dialogue') or [])
    return result
