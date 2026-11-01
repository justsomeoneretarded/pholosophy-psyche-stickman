"""A bounded editorial revision stage, with the actual critiques saved for review.

This does not certify artistic quality. It checks the generated argument and story,
then asks for focused revisions instead of silently weakening the production rules.
"""
import copy
import json
from pathlib import Path

EDITOR_SYSTEM = """You are a rigorous editor of an original animated psychology/philosophy essay.
Review the actual supplied story, not an imagined ideal template.
Find substantive problems: unsupported empirical claims; contradictions; missing reasoning;
unearned cures or guarantees; a reply that does not answer the question actually asked;
an ending that contradicts the argument; visual actions that do not carry the narration.
Consider the producer's intent without copying their sample wording mechanically.
Check that philosophical positions are framed as arguments rather than established universal facts.
Look for a relevant objection and earned reasoning; a gym goal or optimistic slogan alone does not
resolve a philosophical question. Detect repeated explanations and premature jumps to the ending.
Do not forbid fictional dialogue, inner thoughts, complex subjects, humor, or creative structures.
Do not demand generic disclaimers or remove informative depth. A hopeful fictional outcome is
allowed; a universal psychological promise based on that outcome needs revision.
Return JSON only: {"issues":[{"severity":"major"|"minor","beats":[1-based beat numbers;
use 0 for opening/end/publishing metadata],"problem":"specific evidence",
"repair":"concrete editorial change"}],"strengths":["what should be preserved"]}.
List only meaningful issues, not stylistic preferences. Do not invent research or quotations."""

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


def review_concept(sheet, writer, check, title, minutes, output_dir, rounds=2):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    original = copy.deepcopy(sheet)
    (output / 'concept-before-editor.json').write_text(json.dumps(original, indent=1, ensure_ascii=False))
    history = []

    def validate_review(data):
        if not isinstance(data.get('issues'), list):
            raise ValueError('Editor must return an issues list')
        for issue in data['issues']:
            if issue.get('severity') not in ('major', 'minor'):
                raise ValueError('Issue needs severity')
            indices = issue.get('beats')
            if not isinstance(indices, list) or not indices:
                raise ValueError('Issue needs affected beat indices, or [0] for metadata')
            if any(type(i) is not int or i < 0 or i > len(sheet['beats']) for i in indices):
                raise ValueError('Editor referred to a nonexistent beat')
            if not issue.get('problem') or not issue.get('repair'):
                raise ValueError('Issue needs specific evidence and a proposed repair')
        return data

    for round_index in range(rounds + 1):
        report = writer.json(EDITOR_SYSTEM, json.dumps(context(sheet, title), ensure_ascii=False),
                             validate_review, temperature=.25, max_tokens=900, attempts=3)
        history.append({'round': round_index + 1, 'review': report, 'edits': []})
        (output / 'editorial-review.json').write_text(json.dumps(history, indent=1, ensure_ascii=False))
        if not report['issues'] or round_index == rounds:
            break
        selected = sorted({i for issue in report['issues'] for i in issue['beats'] if i})
        batches = [selected[i:i + 2] for i in range(0, len(selected), 2)]
        if any(0 in issue['beats'] for issue in report['issues']):
            batches.append([0])
        for batch in batches:
            issues = [issue for issue in report['issues'] if set(issue['beats']) & set(batch)]
            originals = {str(i): sheet['beats'][i - 1] for i in batch if i}
            payload = {'story': context(sheet, title), 'affected_beats': originals,
                       'requested_indices': batch, 'editorial_findings': issues}
            system = """Revise ONLY the requested parts of this original animated essay.
Preserve the cast, premise, useful distinctions, dramatic acting and informative depth.
Fix the editor's concrete findings; do not replace the film with generic advice.
Return {"edits":[{"beat":requested index, ...only changed beat fields...}],
"metadata":{...only changed opening_line/quote/logo/logline/idea/description/publishing fields...}}.
Use metadata only when index 0 is requested. Preserve the amount of explanatory narration:
shorten redundant visual descriptions rather than removing the argument.
Fictional speech and inner thoughts may appear naturally in narration.
For spoken dialogue retain the existing cast IDs. Never invent empirical facts or quotations."""

            def validate_patch(data):
                candidate = copy.deepcopy(sheet)
                edits = data.get('edits', [])
                if not isinstance(edits, list):
                    raise ValueError('Edits must be a list')
                touched = set()
                for edit in edits:
                    index = edit.get('beat')
                    if index not in batch or index == 0 or index in touched:
                        raise ValueError('Edit refers to an unrequested or duplicate beat')
                    touched.add(index)
                    changes = {k: v for k, v in edit.items() if k != 'beat'}
                    if not set(changes) <= BEAT_FIELDS:
                        raise ValueError('Unknown beat fields')
                    candidate['beats'][index - 1].update(changes)
                if touched != {i for i in batch if i}:
                    raise ValueError('Return a revision for every requested beat')
                metadata = data.get('metadata') or {}
                if metadata and (0 not in batch or not set(metadata) <= META_FIELDS):
                    raise ValueError('Unrequested or unsupported metadata changes')
                candidate.update(metadata)
                problems, _ = check(candidate, minutes)
                # Keep the existing explicit tolerance for a small length mismatch.
                hard = [p for p in problems if 'minutes' not in p]
                if hard:
                    raise ValueError('; '.join(hard[:8]))
                return {'sheet': candidate, 'patch': data}

            revised = writer.json(system, json.dumps(payload, ensure_ascii=False),
                                  validate_patch, temperature=.55, max_tokens=900, attempts=3)
            sheet = revised['sheet']
            history[-1]['edits'].append(revised['patch'])
            (output / 'editorial-review.json').write_text(json.dumps(history, indent=1, ensure_ascii=False))
            (output / 'concept-after-editor.json').write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    return sheet
