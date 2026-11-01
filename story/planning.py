"""Bounded concept, beat expansion and publishing requests for free model limits."""
import copy,json,re
from pathlib import Path
from story.normalization import character_ids

VOCAB=json.loads((Path(__file__).resolve().parents[1]/'engine/vocab.json').read_text())

def supported_location(beat, require_scene=False):
    original=str(beat.get('where') or '')
    if original in VOCAB['sets']:
        if require_scene and original=='scene' and not isinstance(beat.get('scene'),dict):
            raise ValueError('A composed scene needs a scene object; do not leave its environment unspecified')
        return beat
    if isinstance(beat.get('scene'),dict):
        beat['where']='scene'
    else:
        choices=[]
        for name in VOCAB['sets']:
            if name=='scene':continue
            match=re.search(r'(?<![a-z])'+re.escape(name).replace('_',r'[_ ]')+r'(?![a-z])',original.lower())
            if match:choices.append((match.start(),name))
        if choices:
            beat['where']=min(choices)[1]
        elif 'stage' in original.lower():
            beat['where']='scene';beat.setdefault('scene',{'base':'stage','elements':[]})
        else:
            raise ValueError('Unsupported where='+repr(original)+'; choose an exact supported set ID or provide a scene object')
    beat['_location_description']=original
    return beat

def plan_in_parts(writer, system, user, validate, minutes, output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    duration=float(minutes or 4.5)*60
    count=max(12,min(20,round(duration/20)))
    brief=system.split('Return JSON:',1)[0]
    outline_system=brief+"""
OUTLINE REQUEST: Do not write the complete film or publishing package.
Return ONLY this compact JSON:
{"title":"short","idea":{"definition":"one sentence","mechanism":"one sentence","turn":"one sentence","thinkers":"accurate names or empty"},
"approach":"one sentence","cast":[{"id":"short id","kind":"hero|friend|extra|demon","top":"optional color","hair":"optional style","hat":"optional style"}],
"device":{"type":"none|counter|days","items":[{"label":"short","color":"#hex","mode":"cumulative|value"}]},
"inner_voice":null or {"represents":"short","color":"#hex"},
"spine":[{"idea":"short","mode":"story|vignette|metaphor|montage|lesson|inner|contrast|hook",
"where":"supported named set or scene","what_happens":"at most eight words"}]}
Write 5-8 spine entries, each a substantive advance in this particular argument/story.
The spine is not a generic prescribed narrative formula. Preserve causal continuity.
No narration, descriptions, tags, music prompts or full scene objects yet.
Keep the complete outline comfortably below 750 output tokens."""
    def outline_check(data):
        spine=data.get('spine') or data.get('beats')
        if not isinstance(spine,list) or not 5<=len(spine)<=20:
            raise ValueError('Outline needs 5-8 substantive spine entries')
        if not isinstance(data.get('cast'),list) or not data['cast']:
            raise ValueError('Outline needs its cast')
        for entry in spine:supported_location(entry)
        return data
    outline=writer.json(outline_system,user,outline_check,max_tokens=900,temperature=.7,attempts=3)
    (out/'outline.json').write_text(json.dumps(outline,indent=1,ensure_ascii=False))
    spine=outline.get('spine') or outline.get('beats')
    sheet=copy.deepcopy(outline);sheet.pop('spine',None);sheet['beats']=[]
    words=max(20,round(duration*.55*2.45/count))
    history=[]
    local_only=bool(getattr(writer,'specs',None)) and all(s.startswith('ollama:') for s in writer.specs)
    batch_size=1 if local_only else 2
    for start in range(0,count,batch_size):
        indices=list(range(start+1,min(count,start+batch_size)+1))
        slots=[spine[min(len(spine)-1,int((index-1)*len(spine)/count))] for index in indices]
        payload={'topic':user,'argument_and_cast':{k:v for k,v in outline.items() if k not in ('spine','beats')},'requested_indices':indices,
                 'total_beats':count,'spine_entries_to_advance':slots,'previous_beats':sheet['beats'][-2:]}
        def check_chunk(data):
            beats=data.get('beats')
            if len(indices)==1 and beats is None and isinstance(data.get('narration'),list):beats=[data]
            if not isinstance(beats,list) or len(beats)!=len(indices):
                raise ValueError('Return exactly the requested beats')
            prior={' '.join(' '.join(b.get('narration',[])).lower().split()) for b in sheet['beats']}
            for b in beats:
                if not isinstance(b,dict) or not isinstance(b.get('narration'),list):
                    raise ValueError('Each beat needs narration as a sentence list')
                if not isinstance(b.get('who'),list) or not b.get('what_happens'):
                    raise ValueError('Declare the visible cast (or [] for an intentional object shot) and action')
                b['who'],who_problems=character_ids(b['who'],outline['cast'])
                if who_problems:raise ValueError('; '.join(who_problems))
                supported_location(b, require_scene=True)
                text=' '.join(' '.join(b['narration']).lower().split())
                if len(text.split())>=20 and text in prior:
                    raise ValueError('This complete narrated beat duplicates an earlier beat; advance the requested idea instead')
                prior.add(text)
            return beats
        prompt=brief+f"""
EXPANSION REQUEST: Return ONLY {{"beats":[the {len(indices)} requested complete beat objects]}}.
Each beat has: idea, mode, where, seconds, who (cast IDs), emotion, what_happens,
narration (a list of complete sentences), time, weather, grade; optional dialogue
[{{"who":"id","text":"short"}}], inner_voice_line and scene.
Advance ONLY the supplied spine_entries_to_advance. These are beats {indices} of {count};
do not skip to the ending or reuse a different spine entry. Use exact supported set IDs,
not descriptive strings such as park bench or cafe table.
Each beat needs about {words} spoken words in two complete explanatory sentences,
lasting about {duration/count:.0f} seconds. The requested beats advance the spine entry
differently; do not repeat the same explanation or action. Preserve earlier events.
Keep action descriptions to eight words, and omit unused optional fields.
When where=scene include base and a few supported elements with x coordinates.
Otherwise use the named set, without a redundant scene object.
No metadata or publishing fields. Keep this response below 800 output tokens.
"""
        chunk=writer.json(prompt,json.dumps(payload,ensure_ascii=False),check_chunk,
                          max_tokens=900,temperature=.65,attempts=3)
        sheet['beats'].extend(chunk)
        history.append({'first_beat':start+1,'beats':chunk})
        (out/'expanded-beats.json').write_text(json.dumps(history,indent=1,ensure_ascii=False))
    # Publishing prose is separate so it cannot displace narration or truncate the outline.
    pub_system="""Write the publishing package for the supplied finished animated essay.
Return JSON with youtube_titles (3 honest titles), description (2 concise paragraphs plus relevant hashtags),
tags (10 relevant terms), pinned_comment (a specific question), thumbnail_words (2-4 words),
music_prompt (instrumental style suited to this argument), cold_open and ending (optional short lines).
Do not invent research, quotations, search-volume figures or a cure. Do not contradict the essay's conclusion.
Do not claim an intelligence/diagnosis explanation the essay did not establish. Keep below 750 output tokens."""
    publishing=writer.json(pub_system,json.dumps({'topic':user,'film':sheet},ensure_ascii=False),
                           max_tokens=900,temperature=.55,attempts=3)
    allowed={'youtube_titles','description','tags','pinned_comment','thumbnail_words','music_prompt','cold_open','ending'}
    sheet.update({k:v for k,v in publishing.items() if k in allowed})
    (out/'concept-before-validation.json').write_text(json.dumps(sheet,indent=1,ensure_ascii=False))
    return validate(sheet)
