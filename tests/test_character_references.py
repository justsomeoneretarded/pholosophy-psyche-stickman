from story.normalization import character_ids,cast_aliases,dialogue_lines
def test_character_objects_and_symbolic_role_names_preserve_cast_identity():
    cast=[{'id':'alex','kind':'hero'},{'id':'void','kind':'demon'}]
    assert character_ids([{'id':'alex'},'shadow'],cast)==(['alex','void'],[])
    lines,errors=dialogue_lines([{'id':'shadow','line':'What makes this matter?'}],['alex','void'],cast_aliases(cast))
    assert not errors and lines==[{'who':'void','text':'What makes this matter?'}]
