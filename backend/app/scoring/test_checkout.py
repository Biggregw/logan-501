from app.scoring.checkout import suggest_checkouts


def test_double_out_impossible_over_170() -> None:
    assert suggest_checkouts(171, double_out=True) == tuple()


def test_checkout_40_prefers_d20() -> None:
    suggestions = suggest_checkouts(40, double_out=True, limit=3)
    assert suggestions, "expected some suggestions for 40"
    assert suggestions[0].as_strings() == ["D20"]


def test_checkout_50_prefers_dbull_or_d25() -> None:
    suggestions = suggest_checkouts(50, double_out=True, limit=3)
    assert suggestions, "expected some suggestions for 50"
    assert suggestions[0].as_strings() in (["DBULL"], ["D25"])

