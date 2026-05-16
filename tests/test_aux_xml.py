"""Unit tests for .aux.xml read/write backend (no GDAL needed)."""

import pytest
from pathlib import Path
from raster_attr import RasterAttributeTable
from raster_attr.backends import Backend


@pytest.fixture
def sample_rat():
    rat = RasterAttributeTable()
    rat.add_column("Value",     "Integer", "Generic",    values=[11, 21, 31])
    rat.add_column("Count",     "Integer", "PixelCount", values=[500, 1200, 300])
    rat.add_column("ClassName", "String",  "Name",       values=["Shrub", "Grass", "Snow"])
    rat.add_column("MinRefl",   "Real",    "Min",        values=[0.05, 0.10, 0.55])
    return rat


def test_aux_xml_roundtrip(tmp_path, sample_rat):
    raster = tmp_path / "land.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.aux_xml)
    xml_path = tmp_path / "land.tif.aux.xml"
    assert xml_path.exists()

    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
    assert rat2.row_count == 3
    assert rat2.column_count == 4


def test_aux_xml_integer_values(tmp_path, sample_rat):
    raster = tmp_path / "land.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.aux_xml)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
    assert rat2.get_column("Value").values == [11, 21, 31]
    assert rat2.get_column("Count").values == [500, 1200, 300]


def test_aux_xml_string_values(tmp_path, sample_rat):
    raster = tmp_path / "land.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.aux_xml)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
    assert rat2.get_column("ClassName").values == ["Shrub", "Grass", "Snow"]


def test_aux_xml_real_values(tmp_path, sample_rat):
    raster = tmp_path / "land.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.aux_xml)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
    vals = rat2.get_column("MinRefl").values
    assert abs(vals[2] - 0.55) < 1e-6


def test_aux_xml_column_types_preserved(tmp_path, sample_rat):
    raster = tmp_path / "land.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.aux_xml)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
    from raster_attr.column import ColType, ColUsage
    assert rat2.get_column("Value").col_type == ColType.Integer
    assert rat2.get_column("MinRefl").col_type == ColType.Real
    assert rat2.get_column("ClassName").col_type == ColType.String
    assert rat2.get_column("Count").usage == ColUsage.PixelCount
    assert rat2.get_column("MinRefl").usage == ColUsage.Min


def test_aux_xml_overwrite(tmp_path, sample_rat):
    raster = tmp_path / "land.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.aux_xml)
    # Write again with different data
    rat2 = RasterAttributeTable()
    rat2.add_column("Value", "Integer", "Generic", values=[99])
    rat2.to_file(raster, backend=Backend.aux_xml)
    rat3 = RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
    assert rat3.row_count == 1
    assert rat3.get_column("Value").values == [99]


def test_aux_xml_missing_raises(tmp_path):
    raster = tmp_path / "noxml.tif"
    raster.touch()
    with pytest.raises(FileNotFoundError):
        RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)
