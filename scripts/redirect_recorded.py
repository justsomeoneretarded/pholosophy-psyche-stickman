"""Update physical acting while keeping every recorded line and measured scene duration."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from story.director import enrich_film
p=Path(sys.argv[1]); film=json.loads(p.read_text());sheet=json.loads(Path(sys.argv[2]).read_text())
before=[(s['dur'],json.dumps(s.get('lines',[]),sort_keys=True)) for s in film['shots']]
enrich_film(film,sheet)
assert before==[(s['dur'],json.dumps(s.get('lines',[]),sort_keys=True)) for s in film['shots']]
p.write_text(json.dumps(film,indent=1))
print(json.dumps(film['acting_report'],indent=1))
