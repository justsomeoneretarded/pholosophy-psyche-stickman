"""Topic-aware primary-review and encyclopedia background with real source URLs."""
import json,re,urllib.parse,urllib.request
from pipeline.writing.evidence import reviews
API='https://en.wikipedia.org/w/api.php'
HEADERS={'User-Agent':'stickman-essay-studio/1.0 (GitHub Actions; educational video research)'}
THEMES=[
 (r'overthink|ruminat', 'rumination psychology metacognition','rumination[Title/Abstract] AND (metacognition[Title/Abstract] OR repetitive thinking[Title/Abstract]) NOT (psychosis[Title] OR schizophrenia[Title] OR bipolar[Title])'),
 (r'procrastinat', 'procrastination self regulation','procrastination[Title/Abstract]'),
 (r'lonel|alone|isolat', 'loneliness social connection psychology','loneliness[Title/Abstract] AND social[Title/Abstract]'),
 (r'nothing.*matter|nihilis|meaning.*life|existential', 'existential nihilism meaning of life',None),
 (r'social media|never post|instagram', 'social media psychology social comparison','social media[Title/Abstract] AND social comparison[Title/Abstract]'),
 (r'what others think|people.pleas|social approval|fear.*judg', 'social evaluation self esteem psychology','social evaluation[Title/Abstract] AND self esteem[Title/Abstract]'),
 (r'cognitive bias|decision', 'decision making cognitive bias','decision making[Title/Abstract] AND cognitive bias[Title/Abstract]'),
 (r'habit', 'habit psychology behavior change','habit[Title/Abstract] AND behavior change[Title/Abstract]'),
 (r'heartbreak|break.?up|relationship', 'interpersonal relationship attachment theory','romantic relationship[Title/Abstract] AND attachment[Title/Abstract]')
]
def topic_queries(title):
    for pattern,wiki,pubmed in THEMES:
        if re.search(pattern,title,re.I):return wiki,pubmed
    t=re.sub(r'[^\w\s\-]',' ',title)
    t=re.sub(r'\b(why|what|if|how|the|a|an|is|are|do|does|we|you|everything|really)\b',' ',t,flags=re.I)
    return (' '.join(t.split()) or title)+' psychology philosophy',None
def topic_query(title):return topic_queries(title)[0]
def _get(params):
    url=API+'?'+urllib.parse.urlencode({**params,'format':'json','formatversion':2})
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=25) as response:return json.load(response)
def entertainment_page(text):
    return bool(re.search(r'\b(?:is|was)\b.{0,100}\b(?:song|album|single|television series|video game)\b',text[:350],re.I))
def research(title,max_chars=9000):
    sources=[];notes=[];warnings=[]
    query,pubmed=topic_queries(title)
    if pubmed:
        try:
            primary,abstracts=reviews(pubmed,title);sources.extend(primary);notes.extend(abstracts)
            if not primary:warnings.append('No matching PubMed reviews were retrieved')
        except Exception as exc:warnings.append(f'Primary research unavailable: {type(exc).__name__}: {exc}')
    try:
        hits=_get({'action':'query','list':'search','srsearch':query,'srlimit':5}).get('query',{}).get('search',[])
        anchors={'rumination psychology metacognition':['Rumination (psychology)','Metacognition'],
                 'existential nihilism meaning of life':['Nihilism','Meaning of life'],
                 'procrastination self regulation':['Procrastination','Temporal motivation theory']}
        titles=list(dict.fromkeys(anchors.get(query,[])+[h['title'] for h in hits]))[:5]
        if titles:
            # Fetch each canonical page explicitly; extracts otherwise defaults to one page.
            pages=[]
            for requested_title in titles:
                response=_get({'action':'query','prop':'extracts|info','inprop':'url',
                    'explaintext':1,'exintro':1,'redirects':1,'titles':requested_title,'exchars':3500})
                pages.extend(response.get('query',{}).get('pages',[]))
            for page in pages:
                text=re.sub(r'\n{2,}','\n',page.get('extract','')).strip()
                if not text:continue
                if entertainment_page(text) and not re.search(r'song|music|album|film|movie|game',title,re.I):
                    warnings.append('Excluded unrelated entertainment result: '+page.get('title',''));continue
                sources.append({'title':page['title'],'url':page.get('fullurl',''),'source':'Wikipedia','query':query})
                notes.append('## '+page['title']+'\nSource: '+page.get('fullurl','')+'\n'+text)
                if sum(s['source']=='Wikipedia' for s in sources)>=3:break
    except Exception as exc:warnings.append(f'Wikipedia research unavailable: {type(exc).__name__}: {exc}')
    context='\n\n'.join(notes)[:max_chars]
    if not context:warnings.append('No topical sources available; avoid precise unsupported factual claims')
    return {'context':context,'sources':sources,'warnings':warnings,'query':query}
