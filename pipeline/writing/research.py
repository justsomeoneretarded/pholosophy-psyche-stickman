"""Real bibliographic retrieval; metadata is never treated as full-text evidence."""
import requests,re
def research(title):
    sources=[];warnings=[]
    try:
        r=requests.get('https://api.crossref.org/works',params={'query':re.sub(r'[^\w\s]',' ',title),'rows':5,'filter':'type:journal-article','select':'DOI,title,author,published,URL,abstract'},timeout=30);r.raise_for_status()
        for item in r.json()['message']['items']:
            sources.append({'id':f'source_{len(sources)+1}','title':item.get('title',[''])[0],'doi':item['DOI'],'url':item['URL'],'authors':[a.get('family','') for a in item.get('author',[])],'year':item.get('published',{}).get('date-parts',[[None]])[0][0],'abstract':re.sub('<[^>]+>','',item.get('abstract','')),'review_status':'metadata_only'})
    except (requests.RequestException,KeyError,ValueError) as exc:warnings.append('Research retrieval unavailable: '+str(exc))
    warnings.append('Bibliographic relevance is not proof of a claim. Full-text review is not automated; avoid statistics, diagnostic claims and attributed quotations.')
    return sources,warnings
