from story.planning import continuity_history

def test_bounded_history_preserves_full_spoken_facts_and_last_position():
    beat={'narration':['He writes to his brother.'],'dialogue':[{'who':'a','text':'Not sent yet.'}],
          'what_happens':'A drafts a letter.','where':'desk','staging':[
          {'actors':[{'id':'a','pose':'walk','x':10,'to':50}],'scene':{'unused':'x'*10000}},
          {'actors':[{'id':'a','pose':'write','x':50,'hold':'pencil'}]}]}
    history=continuity_history([beat])
    assert history[0]['narration']==beat['narration']
    assert history[0]['dialogue']==beat['dialogue']
    assert history[0]['physical_endpoint'][0]['x']==50
    assert 'staging' not in history[0]
    assert len(str(history))<1000
