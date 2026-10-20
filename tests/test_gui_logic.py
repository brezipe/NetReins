"""Řazení a formátování v tabulce (bez otevírání okna)."""

import gui


def rows():
    return [
        {"name": "zeta.exe", "pid": 30, "down": 5_000, "up": 0, "ldown": None, "lup": None, "drop": None},
        {"name": "(unassigned)", "pid": None, "down": 10, "up": 10, "ldown": None, "lup": None, "drop": None},
        {"name": "Vivaldi.exe", "pid": 20, "down": 200_000, "up": 0, "ldown": 125_000, "lup": None, "drop": 3},
        {"name": "alpha.exe", "pid": 10, "down": 0, "up": 90_000, "ldown": 1_000_000, "lup": None, "drop": None},
    ]


def names(result):
    return [r["name"] for r in result]


def test_default_sort_is_name_a_to_z_with_unassigned_last():
    result = gui.sort_rows(rows(), gui.DEFAULT_SORT, gui.DEFAULT_DESC)
    assert names(result) == ["alpha.exe", "Vivaldi.exe", "zeta.exe", "(unassigned)"]


def test_name_descending_keeps_unassigned_last():
    assert names(gui.sort_rows(rows(), "name", True))[-1] == "(unassigned)"


def test_numeric_sort_descending():
    assert names(gui.sort_rows(rows(), "down", True)) == ["Vivaldi.exe", "zeta.exe", "(unassigned)", "alpha.exe"]


def test_missing_values_are_always_last():
    for desc in (True, False):
        result = gui.sort_rows(rows(), "ldown", desc)
        assert [r["ldown"] for r in result][-2:] == [None, None]


def test_formatting_in_megabits():
    assert gui._fmt_rate(1_000_000) == "8.00"
    assert gui._fmt_limit(None) == "–"
    assert gui._fmt_limit(1_000_000) == "8"
    assert gui._fmt_limit(62_500) == "0.5"
