import pytest
from hypothesis import given, strategies as st

from blackonyx.labeled import (LabeledObject, StrictModeError, lfmt, lit, ljoin, lodict, lolist, source_obj)
from blackonyx.labels import Label, Source, Trust, join


def email(v, n="email#1"):
    return source_obj(v, Source.EMAIL, n)


def test_concat_slice_split_join_index():
    a, b = email("a@x.co,b"), source_obj("tail", Source.WEB, "web#1")
    c = a + b
    assert c.label.sources == Source.EMAIL | Source.WEB and c.label.trust == Trust.UNTRUSTED
    assert a[0:3].label == a.label
    assert a.split(",")[0].label == a.label
    assert ljoin(",", [a, b]).label.sources == Source.EMAIL | Source.WEB
    assert lodict({"k": a})["k"].label == a.label
    assert ("x" + a).label == a.label


def test_user_plus_untrusted_is_untrusted():
    u, e = lit("hello "), email("evil")
    assert (u + e).label.trust == Trust.UNTRUSTED
    assert (u + e).label.sources == Source.USER | Source.EMAIL
    assert (u + lit("x")).label.trust == Trust.USER


def test_strict_mode_blocks_plain_string_escapes():
    e = email("x")
    for fn in (lambda: str(e), lambda: f"{e}", lambda: "%s" % e, lambda: format(e), lambda: int(email("3"))):
        with pytest.raises((StrictModeError, TypeError)):
            fn()
    assert lfmt("to {a}", a=e).label == e.label


def test_nested_list_keeps_item_labels():
    e, w = email("e"), source_obj("w", Source.WEB, "w")
    lst = lolist([e, w])
    assert lst[0].label.sources == Source.EMAIL | Source.WEB


@given(st.lists(st.tuples(st.sampled_from(list(Source)[1:]), st.sampled_from(list(Trust)), st.text(max_size=8)),
                min_size=1, max_size=6))
def test_property_union_and_min(items):
    objs = [LabeledObject(t, Label(s, tr)) for s, tr, t in items]
    expect = join(*[o.label for o in objs])
    acc = objs[0]
    for o in objs[1:]:
        acc = acc + o
    assert acc.label == expect
    assert ljoin(",", objs).label == expect
    assert acc[0:1].label == expect
    assert acc.split(",").label == expect
    for o in objs:
        assert (acc.label.sources & o.label.sources) == o.label.sources
