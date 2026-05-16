"""Unit tests for RatColumn, ColType, ColUsage."""

import pytest
from raster_attr.column import ColType, ColUsage, RatColumn


def test_col_type_values():
    assert ColType.Integer.value == "Integer"
    assert ColType.Real.value == "Real"
    assert ColType.String.value == "String"


def test_col_usage_values():
    assert ColUsage.PixelCount.value == "PixelCount"
    assert ColUsage.Name.value == "Name"
    assert ColUsage.Generic.value == "Generic"


def test_rat_column_init():
    col = RatColumn("Count", ColType.Integer, ColUsage.PixelCount, [10, 20, 30])
    assert col.name == "Count"
    assert col.col_type == ColType.Integer
    assert col.usage == ColUsage.PixelCount
    assert col.values == [10, 20, 30]


def test_rat_column_init_from_strings():
    col = RatColumn("Class", "String", "Name", ["Water", "Forest"])
    assert col.col_type == ColType.String
    assert col.usage == ColUsage.Name


def test_rat_column_default_values():
    col = RatColumn("X", ColType.Real, ColUsage.Generic)
    assert col.values == []


def test_rat_column_repr():
    col = RatColumn("A", ColType.Integer, ColUsage.Generic, [1, 2])
    assert "A" in repr(col)
    assert "Integer" in repr(col)


def test_rat_column_equality():
    c1 = RatColumn("V", ColType.Integer, ColUsage.Generic, [1, 2])
    c2 = RatColumn("V", ColType.Integer, ColUsage.Generic, [1, 2])
    c3 = RatColumn("V", ColType.Integer, ColUsage.Generic, [1, 3])
    assert c1 == c2
    assert c1 != c3


def test_invalid_col_type():
    with pytest.raises(ValueError):
        RatColumn("X", "InvalidType", "Generic")


def test_invalid_col_usage():
    with pytest.raises(ValueError):
        RatColumn("X", "Integer", "InvalidUsage")
