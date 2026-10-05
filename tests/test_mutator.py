import pytest

from eval.mutator import TEXT_ATTACKS, generate
from blackonyx.runner import run


def test_deterministic_and_unique():
    for a in TEXT_ATTACKS:
        v1, v2 = generate(a), generate(a)
        assert v1 == v2 and len(v1) >= 50 and len({v.text for v in v1}) == len(v1)


@pytest.mark.parametrize("a", TEXT_ATTACKS)
def test_metamorphic_same_policy_decision(a):
    base = run(None, a, "D2")
    for v in generate(a, 12):
        r = run(None, a, "D2", variant_text=v.text)
        assert (r.leaked, r.alerts >= 1) == (base.leaked, base.alerts >= 1), v.text
        assert run(None, a, "D0", variant_text=v.text).leaked, f"D0 should obey: {v.text}"
