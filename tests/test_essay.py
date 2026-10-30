import json
import numpy as np
import pytest
from pipeline.animation import setpieces
from pipeline.animation.scene import frame
from pipeline.writing.beats import Script, Beat, compile_script, estimate
from pipeline.writing.essay import check
from pipeline.writing.llm import parse_json
from pipeline.production.essay_mix import build_timeline, script_captions

FIXTURE = 'examples/nihilism-script.json'


def script():
    return Script.model_validate_json(open(FIXTURE).read())


@pytest.mark.parametrize('name', list(setpieces.REGISTRY))
def test_every_setpiece_builds_and_renders(name):
    beat = Beat(mode='silent', setpiece=name, labels=['FEAR', 'TRUTH', 'ESCAPE'], seconds=8, amber=True)
    scene = compile_script(Script(title='Set piece', thesis='Every set piece must render.', beats=[beat] * 4)).scenes[0]
    for t in (.6, scene.duration * .5, scene.duration - .6):
        im = np.asarray(frame(scene, t, (320, 180), ss=1)).astype(float)
        assert im.shape == (180, 320, 3) and im.std() > 3


def test_fixture_compiles_with_silent_and_narrated_beats():
    e = compile_script(script())
    assert any(not s.voiced for s in e.scenes) and any(s.voiced for s in e.scenes)
    assert all(s.style == 'noir' and s.setpiece for s in e.scenes)


def test_length_rules_follow_auto_or_minutes():
    s = script()
    total = sum(estimate(b) for b in s.beats)
    assert check(s, total / 60)[0] == []
    problems, _ = check(s, None)
    assert any('Auto length' in p for p in problems)


def test_checks_reject_invented_claims():
    data = json.loads(open(FIXTURE).read())
    data['beats'][2]['narration'] = 'Studies show that 73 percent of people feel empty. ' + data['beats'][2]['narration']
    problems, _ = check(Script.model_validate(data), None)
    assert any('research' in p for p in problems) and any('statistic' in p for p in problems)


def test_reply_parsing_tolerates_think_blocks_and_fences():
    assert parse_json('<think>planning</think>```json\n{"a": 1}\n```') == {'a': 1}


def test_timeline_fits_narration_and_keeps_silent_beats():
    e = compile_script(script())
    speech = {s.id: {'file': 'x.wav', 'seconds': 10.0, 'words': []} for s in e.scenes if s.voiced}
    silent = {s.id: s.duration for s in e.scenes if not s.voiced}
    timeline, captions = build_timeline(e, speech)
    for row in timeline:
        length = row['end'] - row['start']
        assert length == pytest.approx(silent[row['scene_id']] if not row['voiced'] else 11.35, abs=.01)
    assert captions and captions[0]['start'] > timeline[2]['start']


def test_captions_use_exact_script_words():
    caps = script_captions('Wake up. Work. Eat. Sleep. Repeat.', [{'word': 'wake', 'start': 0, 'end': .3}], 1.0, 3.0)
    assert ' '.join(c['text'] for c in caps) == 'Wake up. Work. Eat. Sleep. Repeat.'
