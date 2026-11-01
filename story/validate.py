"""Check and repair a film (shot list) against engine/vocab.json so it always renders.

python story/validate.py film.json            -> prints problems, writes the repaired film back
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from story.continuity import carry_counters

ROOT = Path(__file__).resolve().parents[1]
VOCAB = json.loads((ROOT / 'engine' / 'vocab.json').read_text())
CARD_STYLES = set(VOCAB['cards'])
INSERTS = set(VOCAB['inserts'])
GRADES = set(VOCAB['grades'])
LINE_STYLES = {'bubble', 'float', 'thought', 'whisper'}
WARDROBE = VOCAB['wardrobe']
HEX = lambda v: isinstance(v, str) and len(v) == 7 and v.startswith('#')


def _num(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


SCENE = VOCAB['scene']


def clean_scene(sc, notes, i):
    sc = dict(sc) if isinstance(sc, dict) else {}
    out = {'base': sc.get('base') if sc.get('base') in SCENE['base'] else 'room'}
    for key in ('wall', 'ground', 'backdrop', 'light'):
        if sc.get(key) in SCENE[key]:
            out[key] = sc[key]
    els = []
    for e in sc.get('elements') or []:
        if not isinstance(e, dict) or e.get('type') not in SCENE['elements']:
            if isinstance(e, dict) and e.get('type'):
                notes.append(f'shot {i}: scene element {e.get("type")!r} is not drawable, skipped')
            continue
        e = {k: v for k, v in e.items() if k in ('type', 'x', 'y', 'w', 'h', 'label', 'color', 'on', 'open', 'front', 'size', 'count',
                                                   'state', 'bottles', 'lamp', 'laptop', 'spin', 'strong', 'on_table')}
        e['x'] = _num(e.get('x'), -5, 105, 50)
        if 'label' in e:
            e['label'] = str(e['label'])[:26]
        for k in ('w', 'size', 'count', 'h', 'y'):
            if k in e and not isinstance(e[k], (int, float)):
                e.pop(k)
        els.append(e)
    out['elements'] = els[:14]
    return out


def repair(film: dict) -> tuple[dict, list[str]]:
    notes: list[str] = []
    film = dict(film)
    film.setdefault('title', 'Untitled')
    cast = {'hero': {'kind': 'hero'}, 'demon': {'kind': 'demon'}}
    for cid, c in (film.get('cast') or {}).items():
        c = dict(c or {})
        if c.get('kind') not in VOCAB['kinds']:
            c['kind'] = 'friend' if cid not in ('hero', 'demon') else cid
        if c.get('hat') and c['hat'] not in VOCAB['hats']:
            c['hat'] = 'beanie_orange'
        if c.get('hair') not in WARDROBE['hair']:
            c.pop('hair', None)
        if c.get('top_style') not in WARDROBE['top_style']:
            c.pop('top_style', None)
        for key in ('top', 'pants', 'scarf', 'hair_color', 'skin', 'iris', 'umbrella_color'):
            if key in c and not isinstance(c[key], str):
                c.pop(key)
        cast[str(cid)] = c
    film['cast'] = cast
    hud = film.get('hud')
    if isinstance(hud, str):
        hud = {'label': hud}
    if isinstance(hud, dict) and hud.get('label') and not hud.get('items'):
        hud = {'items': [{'label': hud['label'], 'color': hud.get('color', '#ffd34a')}]}
    if isinstance(hud, dict) and isinstance(hud.get('items'), list):
        items = [{'label': ' '.join(str(it.get('label', '')).replace('_', ' ').split())[:22], 'color': it.get('color') if HEX(it.get('color')) else '#ffd34a',
                  'mode': 'cumulative' if it.get('mode') == 'cumulative' else 'value'}
                 for it in hud['items'][:2] if isinstance(it, dict) and it.get('label')]
        film['hud'] = {'items': items} if items else None
    else:
        film['hud'] = None
    if not HEX(film.get('demon_color')):
        film['demon_color'] = '#ff2a2a'
    if film.get('narrator') not in ('male', 'female', 'british_male', 'british_female'):
        film['narrator'] = 'male'
    shots = []
    for i, raw in enumerate(film.get('shots') or []):
        if not isinstance(raw, dict):
            continue
        s = dict(raw)
        s['dur'] = round(_num(s.get('dur'), 1.5, 14, 3.2), 2)
        if s.get('set') == 'scene':
            s['scene'] = clean_scene(s.get('scene'), notes, i)
        if s.get('set') not in VOCAB['sets']:
            if s.get('set') and not s.get('card'):
                notes.append(f'shot {i}: unknown set {s.get("set")!r} -> void')
            s['set'] = 'void' if not s.get('card') else s.get('set', 'void')
            if s['set'] not in VOCAB['sets']:
                s['set'] = 'void'
        if s.get('time') not in VOCAB['times']:
            s.pop('time', None)
        if s.get('weather') not in VOCAB['weather']:
            s.pop('weather', None)
        if s.get('grade') not in GRADES:
            s.pop('grade', None)
        if isinstance(s.get('big'), dict) and str(s['big'].get('text', '')).strip():
            s['big'] = {k: v for k, v in s['big'].items() if k in ('text', 'at', 'x', 'y', 'size', 'color')}
            s['big']['text'] = str(s['big']['text'])[:16]
        else:
            s.pop('big', None)
        cam = dict(s.get('camera') or {})
        if cam.get('frame') not in VOCAB['frames']:
            cam['frame'] = 'wide'
        if cam['frame'] == 'phone' and not isinstance(s.get('phone'), dict):
            cam['frame'] = 'close'
        if isinstance(s.get('phone'), dict) and cam['frame'] != 'phone' and not s.get('actors'):
            cam['frame'] = 'phone'
        if cam['frame'] == 'insert' or isinstance(s.get('insert'), dict) and not s.get('actors'):
            ins = s.get('insert') if isinstance(s.get('insert'), dict) else None
            if not ins or ins.get('type') not in INSERTS:
                cam['frame'] = 'wide' if s.get('actors') else 'insert'
                if not s.get('actors'):
                    s['insert'] = {'type': 'note', 'text': str((ins or {}).get('text') or '...')[:40]}
            else:
                cam['frame'] = 'insert'
                if ins['type'] in ('note', 'letter'):
                    ins['text'] = str(ins.get('text') or '...')[:44]
                    s['dur'] = round(max(s['dur'], .8 + len(ins['text']) / 9 + 1.2), 2)
                if ins['type'] == 'calendar':
                    ins['days'] = int(_num(ins.get('days'), 28, 31, 30)); ins['from'] = int(_num(ins.get('from'), 1, ins['days'], 1))
                    ins['marked'] = int(_num(ins.get('marked'), ins['from'], ins['days'], ins['days']))
        s['camera'] = cam
        if cam['frame'] == 'phone':
            ph = s['phone']
            if ph.get('app') not in VOCAB['phone_apps']:
                ph['app'] = 'chat'
            for m in ph.get('messages') or []:
                m['from'] = 'me' if m.get('from') == 'me' else 'them'
                m['text'] = str(m.get('text', ''))[:60]
                m['at'] = _num(m.get('at'), 0, s['dur'], 0)
            ty = ph.get('typing')
            if isinstance(ty, dict):
                ty['text'] = str(ty.get('text', ''))[:48]
                if ty.get('action') not in ('delete', 'send', 'hold'):
                    ty['action'] = 'hold'
                need = _num(ty.get('at'), 0, 9, .4) + len(ty['text']) / 11 + (1.6 if ty['action'] == 'delete' else .9)
                if need > s['dur']:
                    s['dur'] = round(min(9, need), 2)
            elif ty is not None:
                ph.pop('typing')
            empty = {'chat': not ph.get('messages') and not ph.get('typing'), 'lock': not ph.get('notifications'),
                     'call': False, 'feed': False, 'alarm': False}.get(ph['app'], False)
            if empty:
                # a blank screen tells the viewer nothing: show a waiting notification instead
                ph['app'] = 'lock'
                ph['notifications'] = [{'app': 'Messages', 'text': f"{ph.get('contact') or 'new message'}", 'at': .4}]
                notes.append(f'shot {i}: empty phone screen -> lock screen notification')
        if isinstance(s.get('card'), dict):
            cd = s['card']
            if cd.get('style') not in CARD_STYLES:
                cd['style'] = 'title'
            cd['lines'] = [str(x) if cd['style'] in ('line','quote') else str(x)[:48] for x in (cd.get('lines') or [])][:3] or [film['title']]
        elif s.get('card') is not None:
            s.pop('card')
        actors = []
        for a in s.get('actors') or []:
            if not isinstance(a, dict):
                continue
            a = dict(a)
            aid = str(a.get('id', 'hero'))
            if aid not in cast:
                cast[aid] = {'kind': 'extra' if a.get('kind') == 'extra' else 'friend', 'hat': 'beanie_green'}
                notes.append(f'shot {i}: added unknown actor {aid!r} to the cast')
            a['id'] = aid
            if a.get('pose') not in VOCAB['poses']:
                if a.get('pose'):
                    notes.append(f'shot {i}: pose {a.get("pose")!r} -> stand')
                a['pose'] = 'stand'
            if a['pose'] in ('lean', 'grab') and cast.get(aid, {}).get('kind') != 'demon' and not a.get('target'):
                a['pose'] = 'stand'
            if a.get('mood') not in VOCAB['moods']:
                a.pop('mood', None)
            if a.get('hold') not in VOCAB['holds']:
                a.pop('hold', None)
            a['x'] = _num(a.get('x'), 2, 98, 50)
            if 'to' in a:
                a['to'] = _num(a.get('to'), -10, 110, a['x'])
            if a.get('facing') not in (-1, 0, 1):
                a.pop('facing', None)
            for key, lo, hi in (('scale', .3, 1.6), ('opacity', .1, 1), ('at', 0, s['dur'])):
                if key in a:
                    a[key] = _num(a[key], lo, hi, None)
                    if a[key] is None:
                        a.pop(key)
            actors.append(a)
        s['actors'] = actors[:5]
        lines = []
        ids = {a['id'] for a in actors}
        for ln in s.get('lines') or []:
            if not isinstance(ln, dict) or not str(ln.get('text', '')).strip():
                continue
            who = str(ln.get('who', 'caption'))
            if who not in ids and who not in ('caption', 'narrator'):
                who = 'demon' if who == 'demon' else 'caption'
            limit = 150 if who == 'narrator' else 70
            new = {'who': who, 'text': str(ln['text']).strip() if who == 'narrator' else str(ln['text']).strip()[:limit], 'at': _num(ln.get('at'), 0, max(0, s['dur'] - .5), .4)}
            if ln.get('dur') is not None:
                new['dur'] = _num(ln.get('dur'), .8, 9, None)
            if who == 'narrator':
                if str(ln.get('twist') or '').strip():
                    new['twist'] = str(ln['twist']).strip()[:60]
                if ln.get('hidden'):
                    new['hidden'] = True
                words = len((new['text'] + ' ' + new.get('twist', '')).split())
                s['dur'] = round(max(s['dur'], new['at'] + words / 2.5 + 1.2), 2)
            elif ln.get('style') in LINE_STYLES:
                new['style'] = ln['style']
            lines.append({k: v for k, v in new.items() if v is not None})
        s['lines'] = lines[:3]
        if s.get('music') not in VOCAB['music_levels']:
            s.pop('music', None)
        if s.get('transition') not in VOCAB['transitions']:
            s.pop('transition', None)
        s['sfx'] = [x for x in (s.get('sfx') or []) if isinstance(x, dict) and x.get('name') in VOCAB['sfx']]
        s['items'] = [x for x in (s.get('items') or []) if isinstance(x, dict) and x.get('type') in VOCAB['items']]
        h = s.get('hud')
        if isinstance(h, dict):
            ok = lambda v: isinstance(v, (int, float)) or (isinstance(v, list) and len(v) == 2 and all(isinstance(q, (int, float)) for q in v))
            vals = h.get('values') if isinstance(h.get('values'), list) else ([h['value']] if 'value' in h else [])
            vals = [v if ok(v) else None for v in vals][:2]
            h = {'values': vals} if film['hud'] and any(v is not None for v in vals) else {}
            chap = (raw.get('hud') or {}).get('chapter')
            if chap:
                h['chapter'] = str(chap)[:18]
            if (raw.get('hud') or {}).get('reset') is True:
                h['reset'] = True
            if (raw.get('hud') or {}).get('alert'):
                h['alert'] = True
            if h:
                s['hud'] = h
            else:
                s.pop('hud', None)
        else:
            s.pop('hud', None)
        if not s['actors'] and not s.get('card') and cam['frame'] not in ('phone', 'insert'):
            notes.append(f'shot {i}: nothing to show, dropped')
            continue
        shots.append(s)
    if not shots:
        raise ValueError('the film has no usable shots')
    # carry the HUD forward so the counter never blinks off between shots
    last = None
    for s in shots:
        if 'hud' not in s and last is not None and not s.get('card'):
            vals = [v[-1] if isinstance(v, list) else v for v in last.get('values', [])]
            s['hud'] = {k: v for k, v in (('values', vals), ('chapter', last.get('chapter'))) if v}
        if s.get('hud'):
            last = s['hud']
    if not any((s.get('card') or {}).get('style') == 'cta' for s in shots):
        shots.append({'dur': 4.2, 'set': 'void', 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this hit, like and subscribe.']},
                      'actors': [{'id': 'hero', 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}], 'lines': []})
        notes.append('added the closing like/subscribe card')
    shots[0].setdefault('transition', 'fade')
    film['shots'] = shots
    film = carry_counters(film, notes)
    film['duration'] = round(sum(s['dur'] for s in shots), 2)
    return film, notes


if __name__ == '__main__':
    p = Path(sys.argv[1])
    film, notes = repair(json.loads(p.read_text()))
    p.write_text(json.dumps(film, indent=1, ensure_ascii=False))
    print(f'{film["title"]}: {len(film["shots"])} shots, {film["duration"]} s')
    for n in notes:
        print(' -', n)
