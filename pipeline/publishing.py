import json,re,os
from pathlib import Path
def package(episode,timeline,sources,out):
    out=Path(out);title=episode.title
    keywords=list(dict.fromkeys(re.findall(r'\b[a-zA-Z]{5,}\b',title.lower())))+['philosophy','human behavior','animated essay']
    chapters=[]
    for s,row in zip(episode.scenes,timeline):
        if len(episode.scenes)>5 and len(chapters)<8 and (not chapters or row['start']-chapters[-1][0]>=35):chapters.append((row['start'],s.text or s.purpose[:65]))
    description=f'{title}\n\n{episode.thesis}\n\nAn original animated philosophical exploration. Examples are illustrative, not diagnoses or universal personality claims.\n'
    if len(chapters)>=3:description+='\nChapters\n'+'\n'.join(f'{int(t)//60:02}:{int(t)%60:02} '+name for t,name in chapters)+'\n'
    description+='\nBackground reading (retrieved metadata; inclusion does not establish every claim):\n'+'\n'.join(s['title']+' — '+s['url'] for s in sources)
    description+='\n\nOriginal procedural animation and music. Narration uses a separately licensed Piper voice.\n#Philosophy #HumanBehavior\n'
    contents={'youtube_title.txt':title[:100],'youtube_description.txt':description,'keywords.txt':', '.join(keywords),'hashtags.txt':'#Philosophy #HumanBehavior','pinned_comment.txt':'Which example fits your experience, and where would you disagree with the argument?','video_summary.txt':episode.thesis,'content_review_notes.md':'Philosophical exploration. Bibliographic metadata is not full-text fact checking. Review nuance and sources before publishing. Monetization eligibility is not guaranteed.'}
    for name,text in contents.items():(out/name).write_text(text)
    (out/'metadata.json').write_text(json.dumps({'title':title[:100],'description':description[:5000],'tags':keywords,'privacyStatus':'private'},indent=2))
def upload(out):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    out=Path(out);marker=out/'youtube_upload.json'
    if marker.exists():return json.loads(marker.read_text())
    raw=os.environ.get('YOUTUBE_OAUTH_JSON')
    if not raw:raise ValueError('YOUTUBE_OAUTH_JSON required for optional private upload')
    credentials=Credentials.from_authorized_user_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/youtube.upload'])
    youtube=build('youtube','v3',credentials=credentials,cache_discovery=False);meta=json.loads((out/'metadata.json').read_text())
    pending=out/'youtube_upload_pending.json'
    if pending.exists():raise RuntimeError('Previous upload outcome ambiguous; check YouTube Studio before retrying')
    pending.write_text(json.dumps({'title':meta['title'],'status':'in_flight'}))
    result=youtube.videos().insert(part='snippet,status',body={'snippet':{'title':meta['title'],'description':meta['description'],'tags':meta['tags'],'categoryId':'27'},'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}},media_body=MediaFileUpload(str(out/'video.mp4'),chunksize=8*1024*1024,resumable=True)).execute()
    marker.write_text(json.dumps({'id':result['id'],'privacy':'private'}));pending.unlink();return result
