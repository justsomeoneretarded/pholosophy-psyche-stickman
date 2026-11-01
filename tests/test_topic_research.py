from pipeline.writing.research import topic_query,entertainment_page
def test_philosophical_title_is_not_searched_as_a_metallica_song():
    assert 'nihilism' in topic_query('What If Nothing Really Matters?')
    assert 'rumination' in topic_query('Why Smart People Overthink Everything')
def test_unrelated_music_results_are_identified():
    assert entertainment_page('"Nothing Else Matters" is a song by American heavy metal band Metallica.')
    assert not entertainment_page('Nihilism is a family of philosophical views that rejects generally accepted aspects of human existence.')
