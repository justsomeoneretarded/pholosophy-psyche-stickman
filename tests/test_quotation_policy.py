"""Fictional speech is valid narration; real-person attributions need verification."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'story'))
import essay
from pipeline.writing.quotation import has_attributed_quotation
from pipeline.writing.beats import Script
from pipeline.writing.essay import check

FICTION = [
    'He kept asking himself, “What if I get this wrong?”',
    'He asks the adviser, “What do we actually need to know before sending?”',
    'Alex whispered, "I can send an honest message without predicting the reply."',
    "She thought, 'Maybe I can begin before I feel certain.'",
    'He calls the draft “unfinished,” then opens the real conversation.',
]
ATTRIBUTED = [
    'Marcus Aurelius once said, “You must control every possible outcome.”',
    'As Nietzsche wrote: "Make every decision completely certain."',
    '“Happiness requires a perfect plan.” — Seneca',
    '"Certainty is everything," wrote Plato.',
    'Epictetus said, ‘Wait until every doubt disappears.’',
]

def concept(text):
    filler = ['A useful decision changes when new information becomes available.',
              'Repeating the same prediction can leave the next step unchanged.',
              'The character can ask a specific question instead of demanding a guarantee.']
    beats = [{'where': 'bedroom', 'seconds': 12,
              'narration': [text, *filler] if i == 1 else filler if i % 3 else [],
              'demon_line': 'check again.' if i == 0 else ''} for i in range(12)]
    return {'beats': beats}

@pytest.mark.parametrize('text', FICTION)
def test_fictional_quotes_are_allowed_by_active_concept_checker(text):
    assert not has_attributed_quotation(text)
    problems, _ = essay.check_concept(concept(text), None)
    assert not any('quot' in p for p in problems), problems

@pytest.mark.parametrize('text', ATTRIBUTED)
def test_real_thinker_quotations_are_flagged(text):
    assert has_attributed_quotation(text)
    problems, _ = essay.check_concept(concept(text), None)
    assert any('verified source evidence' in p for p in problems), problems

def test_quotes_are_allowed_in_legacy_writer_too():
    script = Script.model_validate_json(Path('examples/nihilism-script.json').read_text())
    data = script.model_dump()
    beat = next(b for b in data['beats'] if b['mode'] == 'narrated')
    beat['narration'] = FICTION[1] + ' ' + beat['narration']
    problems, _, _ = check(Script.model_validate(data), None)
    assert not any('quot' in p for p in problems), problems

def test_prompt_does_not_ban_fictional_quotes():
    prompt = essay.concept_prompt('Overthinking', 4)
    assert 'never in narration' not in prompt
    assert 'quotation marks alone are allowed' in prompt.lower()
