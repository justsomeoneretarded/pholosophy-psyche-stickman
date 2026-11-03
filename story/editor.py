"""A bounded editorial revision stage, with the actual critiques saved for review.

This does not certify artistic quality. It checks the generated argument and story,
then asks for focused revisions instead of silently weakening the production rules.
"""
import copy
import json
from pathlib import Path

EDITOR_SYSTEM = """You are a rigorous editor of an original animated psychology/philosophy essay.
Review the actual supplied story, not an imagined ideal template.
Track the factual state of the fictional events across ALL beats: messages sent, decisions made, replies received, objects moved. A completed event must not repeatedly restart as though it never happened. Distinct follow-up messages are allowed when identified as such. Cite all contradictory beat indices and repair the later reset, preserving the earliest meaningful occurrence.
Find substantive problems: unsupported empirical claims; contradictions; missing reasoning;
unearned cures or guarantees; a reply that does not answer the question actually asked;
an ending that contradicts the argument; visual actions that do not carry the narration.
Consider the producer's intent without copying their sample wording mechanically.
Check that philosophical positions are framed as arguments rather than established universal facts.
Look for a relevant objection and earned reasoning; a gym goal or optimistic slogan alone does not
resolve a philosophical question. Detect repeated explanations and premature jumps to the ending.
Do not forbid fictional dialogue, inner thoughts, complex subjects, humor, or creative structures.
Visual metaphors, talking billboards, imagined advisers and personification are fictional acting,
not supernatural empirical claims. Do not demand literal disclaimers for poetic language.
Do not request merging/deleting indexed beats: repurpose redundant beats into new reasoning or objections.
Do not invent historical corrections from memory; only assert a specific factual error with clear evidence.
Do not demand generic disclaimers or remove informative depth. A hopeful fictional outcome is
allowed; a universal psychological promise based on that outcome needs revision.
Return JSON only: {"issues":[{"severity":"major"|"minor","beats":[1-based beat numbers;
use 0 for opening/end/publishing metadata],"revise":[only the beat indices that must actually change; these may be fewer than beats],"problem":"specific evidence",
"repair":"concrete editorial change"}],"strengths":["what should be preserved"]}.
The beats list is affected context; revise lists only actual patch targets. If beats 10 and 11 repeat, revise only one of them and keep the other as context. Do not tell a patch for beat 10 to edit beat 11.
List only meaningful issues, not stylistic preferences. Do not invent research or quotations. Proposed repairs must not add unsupported neuroscience or research claims. Replace redundant exposition with deeper reasoning instead of deleting beats."""

BEAT_FIELDS = set("""name seconds where time weather grade emotion what_happens narration
demon_line inner_voice_line dialogue phone insert big_text counter_values chapter relapse mode idea scene who""".split())
META_FIELDS = set("""opening_line quote logo logline idea inner_voice description youtube_titles
tags thumbnail_words pinned_comment cold_open ending approach device""".split())


def context(sheet, title):
    return {
        'topic_and_direction': title, 'visual_review_notes': sheet.get('_visual_review_notes', []),
        'idea': sheet.get('idea'), 'logline': sheet.get('logline'), 'device': sheet.get('device'),
        'inner_voice': sheet.get('inner_voice'), 'approach': sheet.get('approach'),
        'cold_open': sheet.get('cold_open'), 'ending': sheet.get('ending'), 'cast': sheet.get('cast'),
        'opening_line': sheet.get('opening_line'), 'quote': sheet.get('quote'),
        'logo': sheet.get('logo'), 'description': sheet.get('description'),
        'beats': [{'index': i + 1, **{k: b.get(k) for k in
                   ('name', 'idea', 'mode', 'where', 'scene', 'who', 'what_happens', 'narration', 'dialogue', 'demon_line', 'inner_voice_line')}}
                  for i, b in enumerate(sheet['beats'])]
    }


def review_concept(sheet, writer, check, title, minutes, output_dir, rounds=2, reviewer=None):
    reviewer=reviewer or writer
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    original=copy.deepcopy(sheet)
    (output/'concept-before-editor.json').write_text(json.dumps(original,indent=1,ensure_ascii=False))
    history=[]
    def save():
        (output/'editorial-review.json').write_text(json.dumps(history,indent=1,ensure_ascii=False))
        (output/'concept-after-editor.json').write_text(json.dumps(sheet,indent=1,ensure_ascii=False))
    def validate_review(data):
        if not isinstance(data.get('issues'),list):raise ValueError('Editor must return an issues list')
        for issue in data['issues']:
            if issue.get('severity') not in ('major','minor'):raise ValueError('Issue needs severity')
            indices=issue.get('beats')
            if not isinstance(indices,list) or not indices:raise ValueError('Issue needs affected beat indices')
            if any(type(i) is not int or not 0<=i<=len(sheet['beats']) for i in indices):raise ValueError('Nonexistent beat')
            targets=issue.get('revise',indices)
            if not isinstance(targets,list) or not targets or any(type(i) is not int or not 0<=i<=len(sheet['beats']) for i in targets):raise ValueError('revise needs valid actual patch target indices')
            if not issue.get('problem') or not issue.get('repair'):raise ValueError('Explain the specific problem and repair')
        return data
    for round_index in range(rounds+1):
        report=reviewer.json(EDITOR_SYSTEM,json.dumps(context(sheet,title),ensure_ascii=False),
                           validate_review,temperature=.25,max_tokens=900,attempts=3)
        history.append({'round':round_index+1,'reviewer':getattr(reviewer,'used',None),'review':report,'edits':[]});save()
        if not report['issues'] or round_index==rounds:break
        selected=sorted({i for issue in report['issues'] for i in issue.get('revise',issue['beats']) if i})
        if any(0 in issue.get('revise',issue['beats']) for issue in report['issues']):selected.append(0)
        for index in selected:
            issues=[issue for issue in report['issues'] if index in issue.get('revise',issue['beats'])]
            payload={'topic_and_direction':title,'argument':sheet.get('idea'),'approach':sheet.get('approach'),
                     'cast':sheet.get('cast'),'requested_beat':index,
                     'story_map':[{'beat':i+1,'idea':b.get('idea'),'action':b.get('what_happens')} for i,b in enumerate(sheet['beats'])],
                     'findings':issues}
            if index:
                payload['current_beat']={k:v for k,v in sheet['beats'][index-1].items() if not k.startswith('_')}
                payload['previous_beat']=sheet['beats'][index-2] if index>1 else None
                payload['next_beat']=sheet['beats'][index] if index<len(sheet['beats']) else None
            else:
                payload['metadata']={k:sheet.get(k) for k in META_FIELDS if k in sheet}
                payload['last_beats']=sheet['beats'][-2:]
            system="""Revise the single requested part of this original animated essay.
For a nonzero requested_beat return {"changes":{only changed beat fields}}.
For requested_beat=0 return {"metadata":{only changed publishing/opening/ending fields}}.
The application applies changes to that fixed part; never return edits to other beats.
Preserve cast, premise, useful distinctions, informative depth and physical acting.
Do not delete a beat or replace fields with null. If exposition repeats, advance its
reasoning or use the slot for a concrete objection/example instead of erasing the slot.
Preserve approximately the current amount of narration. Fictional dialogue is allowed.
Never invent empirical findings, percentages, neuroscience, citations or quotations.
Unsupported universal claims should be qualified or reframed, not given invented evidence.
Use existing cast IDs and supported locations. Dialogue is a list of {who: cast ID, text: speech} objects. Do not include beat/index inside changes. Return JSON only."""
            system += "\nAllowed beat fields: " + ", ".join(sorted(BEAT_FIELDS)) + "\nAllowed metadata fields: " + ", ".join(sorted(META_FIELDS))
            def validate_patch(data):
                history[-1].setdefault('proposals',[]).append({'beat':index,'data':data})
                save()
                candidate=copy.deepcopy(sheet)
                if index:
                    changes=data.get('changes')
                    if changes is None and isinstance(data.get('edits'),list) and len(data['edits'])==1:
                        legacy=data['edits'][0]
                        if legacy.get('beat')!=index:raise ValueError('Edit refers to a different requested beat')
                        changes={k:v for k,v in legacy.items() if k!='beat'}
                    if not isinstance(changes,dict) or not changes:raise ValueError('Return changed fields under changes')
                    changes=dict(changes)
                    if 'beat' in changes:
                        if str(changes.pop('beat'))!=str(index):raise ValueError('Patch identifies a different beat')
                    unknown=set(changes)-BEAT_FIELDS
                    if unknown:raise ValueError('Unknown beat fields: '+', '.join(sorted(unknown))+'; use the existing current_beat field names')
                    if any(v is None for v in changes.values()):raise ValueError('Do not erase fields with null')
                    candidate['beats'][index-1].update(changes)
                    if 'where' in changes or 'scene' in changes:
                        from story.planning import supported_location
                        supported_location(candidate['beats'][index-1],require_scene=True)
                    patch={'beat':index,'changes':changes}
                else:
                    metadata=data.get('metadata')
                    if not isinstance(metadata,dict) or not set(metadata)<=META_FIELDS:raise ValueError('Return supported metadata fields')
                    candidate.update(metadata);patch={'metadata':metadata}
                problems,_=check(candidate,minutes)
                hard=[p for p in problems if 'minutes' not in p]
                if hard:raise ValueError('; '.join(hard[:8]))
                return {'sheet':candidate,'patch':patch}
            revised=writer.json(system,json.dumps(payload,ensure_ascii=False),validate_patch,
                                temperature=.5,max_tokens=900,attempts=3)
            sheet=revised['sheet'];history[-1]['edits'].append(revised['patch']);save()
    if report['issues']:
        print('::warning title=Editorial findings remain::'+str(len(report['issues']))+' findings remain in editorial-review.json',flush=True)
    return sheet
