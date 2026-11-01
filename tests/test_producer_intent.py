from story.essay import check_concept
def test_explicit_producer_message_story_is_not_rejected_as_unrelated_phone_content():
    beats=[{'where':'bedroom','mode':'story','who':['hero'],'seconds':18,
        'what_happens':'He checks his phone and writes a reply.',
        'narration':['He considers whether another revision would clarify his message or merely delay the moment when another person can respond.']} for _ in range(12)]
    title='Why Smart People Overthink Everything. Direction from the producer: Follow a character revising a message to a friend.'
    problems,_=check_concept({'_title':title,'beats':beats},4)
    assert not any('phones or screens' in p for p in problems)
