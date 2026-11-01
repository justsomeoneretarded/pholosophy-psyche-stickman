"""Normalize common model dialogue shapes without discarding any speech."""
def dialogue_lines(value,cast_ids=()):
    if value is None:return [],[]
    known={str(cid).lower():str(cid) for cid in cast_ids}
    if isinstance(value,dict):
        value=[value] if 'who' in value and 'text' in value else [{'who':who,'text':text} for who,text in value.items()]
    if isinstance(value,str):value=[value]
    if not isinstance(value,list):return [],['dialogue must be a list or speaker-to-text mapping']
    out=[];problems=[]
    for line in value:
        if isinstance(line,str) and ':' in line:
            who,text=line.split(':',1);line={'who':who.strip(),'text':text.strip()}
        if not isinstance(line,dict) or not isinstance(line.get('who'),str) or not isinstance(line.get('text'),str):
            problems.append('each dialogue line needs who and text strings');continue
        who=line['who'].strip()
        if known:
            if who.lower() not in known:problems.append('dialogue references an undeclared cast ID: '+who);continue
            who=known[who.lower()]
        out.append({'who':who,'text':line['text'].strip()})
    return out,problems
