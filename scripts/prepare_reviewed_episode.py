"""Compile an explicit AI editorial revision, independently reviewed before production."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from story.essay import stage_concept,stage_merge
root=Path('build');writing=root/'writing'
title='Why Smart People Overthink Everything. Direction from the producer: Follow Alex drafting a message after Jamie says Friday looks tight; keep ownership of each message clear, resolve the one unfinished review through conversation, and distinguish investigation from rehearsal. This explicit AI editorial revision is a production review, not an unattended writing benchmark.'
research=(writing/'research.txt').read_text() if (writing/'research.txt').exists() else ''
stage_concept(title,6,writing,research,reuse_draft=Path('examples/overthinking-reviewed-draft.json'),review=True)
(writing/'shots.json').write_text(Path('examples/overthinking-reviewed-shots.json').read_text())
stage_merge(writing,root/'film.json')
