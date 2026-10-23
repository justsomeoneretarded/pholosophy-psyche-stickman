from pipeline.writing.story import normalize_scene
from pipeline.models import Scene
def test_known_model_errors_are_repaired_without_dropping_actions():
    raw={'id':'s1','purpose':'Inspect the blank page','narration':'He sits at a wooden table and considers what the blank page could become.','duration':20,'characters':['main'],'props':[{'id':'wooden_table','kind':'table','x':.35,'y':.65},{'id':'book','kind':'book','x':.35,'y':.65}],'actions':[{'action':'sit','end':0,'target':'wooden table'},{'action':'think','start':0,'end':10,'target':'blank page'}],'symbol':None}
    repaired,notes=normalize_scene(raw)
    scene=Scene.model_validate(repaired)
    assert len(scene.actions)==2
    assert scene.actions[0].target=='wooden_table'
    assert scene.actions[1].target=='book'
    assert scene.actions[0].end>scene.actions[0].start
    assert scene.symbol=='none'
    assert notes
