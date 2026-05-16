"""Unit tests for RasterAttributeTable core operations."""

import pandas as pd
import pytest

from raster_attr import RasterAttributeTable
from raster_attr.column import ColType, ColUsage


@pytest.fixture
def small_rat():
    rat = RasterAttributeTable()
    rat.add_column("Value", "Integer", "Generic", values=[1, 2, 3])
    rat.add_column("Count", "Integer", "PixelCount", values=[100, 200, 50])
    rat.add_column("ClassName", "String", "Name", values=["Water", "Forest", "Urban"])
    return rat


def test_row_count(small_rat):
    assert small_rat.row_count == 3


def test_column_count(small_rat):
    assert small_rat.column_count == 3


def test_column_names(small_rat):
    assert small_rat.column_names == ["Value", "Count", "ClassName"]


def test_add_column_mismatch_raises(small_rat):
    with pytest.raises(ValueError, match="3 rows"):
        small_rat.add_column("Extra", "Integer", "Generic", values=[1, 2])


def test_add_column_auto_fill(small_rat):
    small_rat.add_column("Area", "Real", "Generic")
    col = small_rat.get_column("Area")
    assert col.values == [0, 0, 0]


def test_remove_column(small_rat):
    small_rat.remove_column("Count")
    assert "Count" not in small_rat.column_names


def test_remove_column_missing_raises(small_rat):
    with pytest.raises(KeyError):
        small_rat.remove_column("NonExistent")


def test_get_column(small_rat):
    col = small_rat.get_column("ClassName")
    assert col.values == ["Water", "Forest", "Urban"]


def test_get_column_missing_raises(small_rat):
    with pytest.raises(KeyError):
        small_rat.get_column("Missing")


def test_to_dataframe(small_rat):
    df = small_rat.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Value", "Count", "ClassName"]
    assert len(df) == 3
    assert df["Value"].dtype == "int64"
    assert df["ClassName"].dtype == object


def test_from_dataframe():
    df = pd.DataFrame({
        "Value": [1, 2, 3],
        "Name": ["A", "B", "C"],
        "Area": [1.5, 2.5, 3.5],
    })
    rat = RasterAttributeTable.from_dataframe(df)
    assert rat.row_count == 3
    assert rat.column_count == 3
    assert rat.get_column("Area").col_type == ColType.Real
    assert rat.get_column("Value").col_type == ColType.Integer
    assert rat.get_column("Name").col_type == ColType.String


def test_from_dataframe_with_usages():
    df = pd.DataFrame({"Value": [1, 2], "Count": [100, 200]})
    rat = RasterAttributeTable.from_dataframe(
        df, usages={"Value": "Generic", "Count": "PixelCount"}
    )
    assert rat.get_column("Count").usage == ColUsage.PixelCount


def test_roundtrip_dataframe(small_rat):
    df = small_rat.to_dataframe()
    rat2 = RasterAttributeTable.from_dataframe(df)
    # Values should match
    assert rat2.get_column("ClassName").values == ["Water", "Forest", "Urban"]
    assert rat2.get_column("Count").values == [100, 200, 50]


def test_repr(small_rat):
    r = repr(small_rat)
    assert "rows=3" in r
    assert "Value" in r


def test_len(small_rat):
    assert len(small_rat) == 3


def test_equality(small_rat):
    rat2 = small_rat.copy()
    assert small_rat == rat2


def test_inequality_after_modification(small_rat):
    rat2 = small_rat.copy()
    rat2.get_column("Value").values[0] = 999
    assert small_rat != rat2


def test_copy_is_independent(small_rat):
    rat2 = small_rat.copy()
    rat2.get_column("Value").values[0] = 999
    assert small_rat.get_column("Value").values[0] == 1


def test_empty_rat():
    rat = RasterAttributeTable()
    assert rat.row_count == 0
    assert rat.column_count == 0
    assert len(rat) == 0


def test_first_column_sets_row_count():
    rat = RasterAttributeTable()
    rat.add_column("V", "Integer", "Generic", values=[10, 20, 30])
    assert rat.row_count == 3
