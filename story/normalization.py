"""Normalize common model character/dialogue shapes without discarding their meaning."""
def cast_aliases(cast):
    aliases={}
    roles={'hero':['hero','main','protagonist'],'friend':['friend'],
           'demon':['demon','shadow','silhouette','void','inner_voice','adviser','advisor']}
    for kind,names in roles.items():
        ids=[str(p['id']) for p in cast if isinstance(p,dict) and p.get('kind')==kind and p.get('id')]
        if len(ids)==1:
            for name in names:aliases[name]=ids[0]
    return aliases

def character_ids(value,cast):
    known={str(p['id']).lower():str(p['id']) for p in cast if isinstance(p,dict) and p.get('id')}
    aliases=cast_aliases(cast)
    if isinstance(value,(str,dict)):value=[value]
    if not isinstance(value,list):return [],['who must be a list of declared cast IDs']
    out=[];problems=[]
    for item in value:
        if isinstance(item,dict):item=item.get('id',item.get('who',item.get('name')))
        if not isinstance(item,str):problems.append('character reference needs a string ID');continue
        key=item.strip().lower()
        resolved=known.get(key) or aliases.get(key)
        if not resolved and known:problems.append('undeclared character ID: '+item);continue
        resolved=resolved or item.strip()
        if resolved not in out:out.append(resolved)
    return out,problems

def dialogue_lines(value,cast_ids=(),aliases=None):
    if value is None:return [],[]
    aliases=aliases or {}
    known={str(cid).lower():str(cid) for cid in cast_ids}
    if isinstance(value,dict):
        speaker=value.get('who',value.get('speaker',value.get('id')))
        content=value.get('text',value.get('line',value.get('utterance')))
        value=[{'who':speaker,'text':content}] if speaker is not None and content is not None else [{'who':who,'text':text} for who,text in value.items()]
    if isinstance(value,str):value=[value]
    if not isinstance(value,list):return [],['dialogue must be a list or speaker-to-text mapping']
    out=[];problems=[]
    for line in value:
        if isinstance(line,str) and ':' in line:
            who,text=line.split(':',1);line={'who':who.strip(),'text':text.strip()}
        if isinstance(line,dict):
            line={'who':line.get('who',line.get('speaker',line.get('id'))),
                  'text':line.get('text',line.get('line',line.get('utterance')))}
        if not isinstance(line,dict) or not isinstance(line.get('who'),str) or not isinstance(line.get('text'),str):
            problems.append('each dialogue line needs who and text strings');continue
        who=line['who'].strip()
        if known:
            resolved=known.get(who.lower()) or aliases.get(who.lower())
            if not resolved:problems.append('dialogue references an undeclared cast ID: '+who);continue
            who=resolved
        out.append({'who':who,'text':line['text'].strip()})
    return out,problems
