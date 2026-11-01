"""Print a good moment for a thumbnail frame: the first close shot where the demon speaks."""
import json
import sys

film = json.load(open(sys.argv[1]))
t = 0.0
for s in film['shots']:
    if any(l['who'] == 'demon' for l in s.get('lines', [])) and s.get('camera', {}).get('frame') in ('close', 'two', 'medium'):
        print(round(t + s['dur'] * 0.75, 2))
        break
    t += s['dur']
else:
    print(3)
