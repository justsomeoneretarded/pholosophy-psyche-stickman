"""Continuity for explicitly cumulative counters; ordinary values may decrease."""
def carry_counters(film, notes):
    items=(film.get('hud') or {}).get('items', [])
    last=[None]*len(items)
    for index, shot in enumerate(film['shots']):
        hud=shot.get('hud') or {}
        values=hud.get('values', [])
        for i,item in enumerate(items):
            if i>=len(values) or values[i] is None:continue
            value=values[i]
            start,end=(value if isinstance(value,list) else [value,value])
            if item.get('mode')=='cumulative' and not hud.get('reset'):
                floor=last[i]
                if floor is not None and start<floor:
                    start=floor
                end=max(start,end)
                if [start,end] != (value if isinstance(value,list) else [value,value]):
                    notes.append(f'shot {index}: preserved cumulative {item["label"]} counter')
                values[i]=[start,end] if isinstance(value,list) else end
            last[i]=end
    return film
