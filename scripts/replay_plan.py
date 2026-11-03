"""Recompile a saved edited concept and its shots without repeating successful AI calls."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from story.essay import stage_concept,stage_merge,minutes_value
def replay(source,title,minutes):
    source=Path(source);writing=source/'writing'
    fixture=source/'film.json'
    if fixture.exists():
        data=json.loads(fixture.read_text())
        if data.get('_regression_fixture') is True:
            from story.validate import repair
            from story.essay import script_md
            data.setdefault('writer','Explicit editorial regression fixture')
            data,notes=repair(data)
            fixture.write_text(json.dumps(data,indent=1))
            script_md(data,source/'story.md')
            print('Rendering explicitly authored regression fixture through the production pipeline',notes)
            return data
    raw=writing/'concept-after-editor.json'
    if not raw.exists():raw=writing/'beats.json'
    data=json.loads(raw.read_text())
    previous=json.loads((writing/'beats.json').read_text()) if (writing/'beats.json').exists() else {}
    data['_writer']=data.get('_writer') or previous.get('_writer')
    review_file=writing/'editorial-review.json'
    if review_file.exists():
        history=json.loads(review_file.read_text())
        if history and any(issue.get('severity')=='major' for issue in history[-1]['review']['issues']):
            raise ValueError('Saved draft has unresolved major editorial findings; revise the checkpoint before production')
    repaired=writing/'replay-input.json';repaired.write_text(json.dumps(data,indent=1,ensure_ascii=False))
    research=(writing/'research.txt').read_text() if (writing/'research.txt').exists() else ''
    direction=str(previous.get('_title','')).partition('Direction from the producer:')[2]
    validation_title=title+('. Direction from the producer: '+direction if direction else '')
    stage_concept(validation_title,minutes_value(minutes),writing,research,repaired,review=False)
    if not (writing/'shots.json').exists():raise ValueError('Saved plan has no completed storyboard')
    return stage_merge(writing,source/'film.json')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--title',required=True);p.add_argument('--minutes',default='auto');a=p.parse_args()
    replay(a.source,a.title,a.minutes)
