"""Repair legacy checkpoint scene data without changing its spoken script."""
import copy,json,re
from pathlib import Path
from story.planning import supported_location
from story.staging import validate_staging,staging_contract

def repair_checkpoint(sheet,writer,output):
    sheet=copy.deepcopy(sheet);history=[];out=Path(output);out.mkdir(parents=True,exist_ok=True)
    for i,beat in enumerate(sheet['beats']):
        try:
            supported_location(beat,require_scene=True);validate_staging(beat,sheet['cast'])
            continue
        except ValueError as exc:error=str(exc)
        original=copy.deepcopy(beat)
        payload={'beat':original,'cast':sheet['cast'],'error':error,'supported':staging_contract()}
        def validate(data):
            candidate=data.get('beat');extras=data.get('extra_cast',[])
            if not isinstance(candidate,dict) or not isinstance(extras,list):raise ValueError('Return beat object and extra_cast list')
            for field in ('narration','dialogue'):
                if candidate.get(field)!=original.get(field):raise ValueError('Schema repair must preserve exact '+field)
            known={p['id'] for p in sheet['cast']}
            for person in extras:
                if not isinstance(person,dict) or person.get('kind')!='extra' or not re.fullmatch(r'[a-z][a-z0-9_]{0,11}',str(person.get('id',''))):
                    raise ValueError('An extra needs a short lowercase ID and kind=extra')
                if person['id'] in known:raise ValueError('Do not overwrite or duplicate cast identities')
                known.add(person['id'])
            supported_location(candidate,require_scene=True);validate_staging(candidate,sheet['cast']+extras)
            return {'beat':candidate,'extra_cast':extras}
        fixed=writer.json(
            'Repair only the unrenderable visual data of this saved AI beat. Return {"beat":complete revised beat,"extra_cast":[]} as JSON. '
            'Preserve narration and dialogue exactly, plus existing cast identities. Use the exhaustive supported contract. '
            'Named sets (street,desk,park) go in where; scene.base is room/outside/nature/void/stage. '
            'Paper/book are not scene elements: use write/read poses and pencil/book holds. Use floor_lamp instead of lamp and streetlamp instead of streetlight. '
            'People are actors, not scene elements: when the spoken scene requires an undeclared person, add a distinguishable kind=extra cast entry and stage that person. '
            'Make the visual action match the existing spoken passage. Do not silently drop a person or important narrative object. '
            'A composed scene needs actual supported elements. Return only the requested beat and necessary extra_cast, under 1200 tokens.',
            json.dumps(payload,ensure_ascii=False),validate,max_tokens=1400,temperature=.2,attempts=3)
        sheet['beats'][i]=fixed['beat'];sheet['cast'].extend(fixed['extra_cast'])
        history.append({'beat':i+1,'original':original,'error':error,'repair':fixed,'writer':writer.used})
        (out/'checkpoint-schema-repairs.json').write_text(json.dumps(history,indent=1,ensure_ascii=False))
    return sheet
