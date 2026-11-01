"""Retrieve real PubMed review records; never synthesize citations."""
import re,json,urllib.parse,urllib.request,xml.etree.ElementTree as ET
BASE='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
HEADERS={'User-Agent':'stickman-essay-studio/1.0 educational research'}
def _read(endpoint,params):
    request=urllib.request.Request(BASE+endpoint+'?'+urllib.parse.urlencode(params),headers=HEADERS)
    with urllib.request.urlopen(request,timeout=25) as response:return response.read()
def reviews(query,topic=''):
    search=json.loads(_read('esearch.fcgi',{'db':'pubmed','term':query+' AND (review[pt] OR meta-analysis[pt])','retmode':'json','retmax':6,'sort':'relevance'}))
    ids=search.get('esearchresult',{}).get('idlist',[])
    if not ids:return [],[]
    root=ET.fromstring(_read('efetch.fcgi',{'db':'pubmed','id':','.join(ids),'retmode':'xml'}))
    sources=[];notes=[]
    for article in root.findall('.//PubmedArticle'):
        pmid=article.findtext('.//MedlineCitation/PMID')
        title=''.join(article.find('.//ArticleTitle').itertext()) if article.find('.//ArticleTitle') is not None else ''
        abstract=' '.join(''.join(a.itertext()) for a in article.findall('.//Abstract/AbstractText'))
        if not pmid or not title or not abstract:continue
        specialized=[r'gene|genetic|molecular',r'psychosis|schizophren',r'childhood|adolescen']
        if any(re.search(term,title,re.I) and not re.search(term,topic,re.I) for term in specialized):continue
        url='https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/'
        source={'title':title,'url':url,'source':'PubMed-indexed review','pmid':pmid,'query':query}
        doi=next((a.text for a in article.findall('.//ArticleId') if a.get('IdType')=='doi'),None)
        if doi:source['doi']=doi
        sources.append(source)
        notes.append('## '+title+'\nSource: '+url+'\nReview abstract excerpt (preserve its population, uncertainty and limitations):\n'+abstract[:1100])
        if len(sources)>=2:break
    return sources,notes
