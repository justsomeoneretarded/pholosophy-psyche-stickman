from pipeline.models import Episode,Scene,Action
from pipeline.writing.quality import assess
def episode(narration):
    return Episode(title='Why We Procrastinate',thesis='Beginning a small task can give information that waiting cannot.',metaphor='The blank document becomes a visible decision.',framing='philosophical_exploration',scenes=[Scene(id='s1',purpose='Open the question',narration=narration,duration=10,actions=[Action(action='think',end=10)]),Scene(id='s2',purpose='Resolve the distinction',narration='One small beginning does not remove every obstacle, but it makes the next decision more concrete.',duration=10,actions=[Action(action='wave',end=10)])])
def test_uncited_empirical_claim_stops_production():
    assert not assess(episode('Studies show that people who procrastinate are always afraid of success.'))['passed']
def test_illustrative_exploration_can_pass_without_fake_citations():
    assert assess(episode('Imagine a blank document. You postpone a sentence because the whole task feels too large.'))['passed']
def test_no_viewer_diagnosis():
    assert not assess(episode('If you procrastinate, you have ADHD and should recognize it.'))['passed']
