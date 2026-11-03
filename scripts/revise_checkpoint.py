"""Continue editorial work on a preserved draft; never regenerate successful source research."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from story.essay import stage_concept,stage_shots,stage_merge
root=Path(sys.argv[1]);writing=root/'writing'
saved=json.loads((writing/'beats.json').read_text())
draft=writing/'concept-after-editor.json'
title=saved.get('_title') or saved['title']
research=(writing/'research.txt').read_text() if (writing/'research.txt').exists() else ''
stage_concept(title,6,writing,research,reuse_draft=draft,review=True)
stage_shots(writing)
stage_merge(writing,root/'film.json')
