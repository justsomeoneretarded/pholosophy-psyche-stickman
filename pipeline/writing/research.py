"""Background reading for the writer: Wikipedia articles about the topic (free, no key).

The writer uses this to keep thinkers, dates and ideas accurate. It is context,
not a fact-checker: prompts still forbid invented quotes, statistics and studies.
"""
import json
import re
import urllib.parse
import urllib.request

API = 'https://en.wikipedia.org/w/api.php'
HEADERS = {'User-Agent': 'stickman-essay-studio/1.0 (GitHub Actions; educational video research)'}


def _get(params):
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
        return json.load(r)


def topic_query(title):
    t = re.sub(r'[^\w\s\-]', ' ', title)
    t = re.sub(r'\b(why|what|how|the|a|an|is|are|do|does|we|you|everything|really|belief in nothing)\b', ' ', t, flags=re.I)
    return ' '.join(t.split()) or title


def research(title, max_chars=9000):
    sources, notes, warnings = [], [], []
    try:
        hits = _get({'action': 'query', 'list': 'search', 'srsearch': topic_query(title), 'srlimit': 4}).get('query', {}).get('search', [])
        titles = [h['title'] for h in hits][:3]
        if titles:
            pages = _get({'action': 'query', 'prop': 'extracts|info', 'inprop': 'url', 'explaintext': 1,
                          'exsectionformat': 'plain', 'titles': '|'.join(titles), 'exchars': 6000}).get('query', {}).get('pages', [])
            order = {t: i for i, t in enumerate(titles)}
            for p in sorted(pages, key=lambda p: order.get(p.get('title'), 9)):
                text = re.sub(r'\n{2,}', '\n', p.get('extract', '')).strip()
                if not text:
                    continue
                sources.append({'title': p['title'], 'url': p.get('fullurl', ''), 'source': 'Wikipedia'})
                notes.append(f"## {p['title']}\n{text}")
    except Exception as exc:  # noqa: BLE001 -- the writer can still work from general knowledge
        warnings.append(f'Wikipedia research unavailable: {type(exc).__name__}: {exc}')
    context = '\n\n'.join(notes)[:max_chars]
    return {'context': context, 'sources': sources, 'warnings': warnings}
