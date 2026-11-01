"""Generate full scripts in bounded requests instead of exceeding free output caps."""
import copy,json,math
from pathlib import Path

def plan_in_parts(writer, system, user, validate, minutes, output_dir):
    out=Path(output_dir)
    duration=float(minutes or 4.5)*60
    count=max(12,min(20,round(duration/20)))
    outline_system=system+f"""
PRODUCTION REQUEST OVERRIDE: Return a compact outline, not the complete beat objects yet.
Use {count} outline entries under beats, each containing ONLY idea, mode, where and what_happens
(a brief visible action). Preserve title, idea, approach, cast, inner_voice, device, music_prompt,
description, youtube_titles, tags, pinned_comment, thumbnail_words, cold_open and ending.
Keep metadata concise. Plan a coherent argument with meaningful differences between its examples.
Subsequent requests will expand each outline entry with narration and staging.
Return JSON, within 900 output tokens."""
    def outline_check(data):
        beats=data.get('beats')
        if not isinstance(beats,list) or not 9<=len(beats)<=20:
            raise ValueError('Outline needs 9-20 beats')
        if not isinstance(data.get('cast'),list) or not data['cast']:
            raise ValueError('Outline needs its cast')
        return data
    outline=writer.json(outline_system,user,outline_check,max_tokens=900,temperature=.7,attempts=3)
    (out/'outline.json').write_text(json.dumps(outline,indent=1,ensure_ascii=False))
    sheet=copy.deepcopy(outline)
    sheet['beats']=[]
    words=max(26,round(duration*.62*2.45/len(outline['beats'])))
    history=[]
    for start in range(0,len(outline['beats']),2):
        requested=outline['beats'][start:start+2]
        payload={'topic':user,'outline':outline,'requested_indices':list(range(start+1,start+len(requested)+1)),
                 'previous_beat':sheet['beats'][-1:] }
        def check_chunk(data):
            beats=data.get('beats')
            if not isinstance(beats,list) or len(beats)!=len(requested):
                raise ValueError('Return exactly the requested beats')
            for b in beats:
                if not isinstance(b,dict) or not isinstance(b.get('narration'),list):
                    raise ValueError('Each beat needs narration as a sentence list')
                if not b.get('who') or not b.get('what_happens'):
                    raise ValueError('Stage the characters and visible action')
            return beats
        prompt=system+f"""
EXPANSION REQUEST: Expand ONLY requested_indices from the supplied outline.
Return {{"beats":[complete requested beat objects]}}. Preserve the outline's argument and causal
continuity; earlier events already happened. Each requested beat should contain approximately
{words} narration words in 2-3 complete sentences, with concrete action, cast IDs, mode, where,
seconds (about {duration/len(outline['beats']):.0f}), emotion, time, weather and grade.
Use supported named sets or provide a complete small scene. No metadata in this response.
Keep visual descriptions compact so narration fits within 900 output tokens.
The full film must retain the outline's distinct places and explanatory modes.
"""
        chunk=writer.json(prompt,json.dumps(payload,ensure_ascii=False),check_chunk,
                          max_tokens=900,temperature=.65,attempts=3)
        sheet['beats'].extend(chunk)
        history.append({'first_beat':start+1,'beats':chunk})
        (out/'expanded-beats.json').write_text(json.dumps(history,indent=1,ensure_ascii=False))
    sheet['_title']=user
    # The same full-film checker still runs; splitting never bypasses editorial requirements.
    return validate(sheet)
