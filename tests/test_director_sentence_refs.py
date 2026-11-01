from story.essay import place_narration
def test_director_sentence_indices_choose_the_matching_action_without_echoing_speech():
    beat={'narration':['He checks the phone.','Then he looks at his friend.']}
    shots=[{'dur':2,'actors':[{'id':'hero','x':20,'pose':'walk','to':40}]},
           {'dur':3,'narration_index':0,'actors':[{'id':'hero','x':40,'pose':'phone'}]},
           {'dur':3,'narration_index':1,'actors':[{'id':'hero','x':40,'pose':'stand'}]}]
    result=place_narration(beat,shots)
    assert not result[0]['lines']
    assert result[1]['lines'][0]['text']=='He checks the phone.'
    assert result[2]['lines'][0]['text']=='Then he looks at his friend.'
