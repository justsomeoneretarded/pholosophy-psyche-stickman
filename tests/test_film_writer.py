import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'story'))
import essay  # noqa: E402
from validate import repair  # noqa: E402


def beat(n=2, demon=''):
    sentences = ['Addiction is not a lack of willpower.', 'It is a lesson the brain learned too well.', 'Every reward teaches it where to look.'][:n]
    return {'where': 'bedroom', 'time': 'night', 'grade': 'night', 'emotion': 'tired', 'narration': sentences, 'demon_line': demon}


def test_every_narration_sentence_is_placed_once_in_order():
    shots = [{'dur': 3, 'camera': {'frame': 'wide'}, 'actors': [{'id': 'hero', 'x': 50, 'pose': 'sit'}],
              'lines': [{'who': 'narrator', 'text': 'a line the model made up'}]}]
    placed = essay.place_narration(beat(3), shots)
    said = [l['text'] for s in placed for l in s['lines'] if l['who'] == 'narrator']
    assert said == beat(3)['narration']
    assert all(sum(1 for l in s['lines'] if l['who'] == 'narrator') <= 1 for s in placed)


def test_inner_voice_line_is_staged_when_missing():
    shots = essay.ensure_demon(beat(1, 'just one more.'), essay.place_narration(beat(1), essay.fallback_shots(beat(1))))
    assert any(l['who'] == 'demon' and l['text'] == 'just one more.' for s in shots for l in s['lines'])


def test_long_sentences_are_split_for_captions():
    parts = essay.split_sentences('This is a very long sentence ' * 12 + 'that ends here.')
    assert all(len(p) <= 150 for p in parts) and len(parts) > 1


def test_concept_checks_length_and_honesty():
    modes = ['story', 'lesson', 'montage', 'metaphor', 'vignette', 'inner']
    beats = [dict(beat(3 if i % 3 else 0, 'go on.' if i % 4 == 0 else ''), seconds=10, mode=modes[i % 6], who=['hero'], where=['bedroom', 'park', 'cafe', 'rooftop', 'street', 'desk', 'hill'][i % 7]) for i in range(12)]
    for b in beats:
        b['narration'] = [x + ' And it keeps teaching him, night after night.' for x in b['narration']]
    ok, total = essay.check_concept({'beats': beats}, None)
    assert ok == [], ok
    assert 180 < total < 400
    beats[1]['narration'] = ['Studies show that 80 percent of people relapse.']
    problems, _ = essay.check_concept({'beats': beats}, None)
    assert any('statistic' in p for p in problems) and any('research' in p for p in problems)


def test_template_films_are_rejected():
    beats = [dict(beat(3, ''), seconds=10, mode='story', where='bedroom', what_happens='he scrolls his phone at 3am') for _ in range(12)]
    sheet = {'beats': beats, '_title': 'Grief'}
    problems, _ = essay.check_concept(sheet, None)
    text = ' '.join(problems)
    assert 'phones' in text and 'stock details' in text and 'no people' in text
    assert len(sheet['_visual_review_notes']) == 2


def test_fallback_film_repairs_and_renders_contract():
    film = {'title': 'Test', 'cast': {}, 'shots': essay.place_narration(beat(2), essay.fallback_shots(beat(2)))}
    film, _ = repair(film)
    assert film['duration'] > 5 and any(l['who'] == 'narrator' for s in film['shots'] for l in s['lines'])
