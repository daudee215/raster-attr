"""Unit tests for .vat.dbf read/write backend (no GDAL needed)."""

import pytest
from pathlib import Path
from raster_attr import RasterAttributeTable
from raster_attr.backends import Backend


@pytest.fixture
def sample_rat():
    rat = RasterAttributeTable()
    rat.add_column("Value", "Integer", "Generic", values=[1, 2, 3, 4])
    rat.add_column("Count", "Integer", "PixelCount", values=[1000, 5000, 2500, 750])
    rat.add_column("ClassName", "String", "Name", values=["Water", "Forest", "Urban", "Bare"])
    rat.add_column("Albedo", "Real", "Generic", values=[0.08, 0.12, 0.25, 0.35])
    return rat


def test_vat_dbf_roundtrip(tmp_path, sample_rat):
    raster = tmp_path / "landcover.tif"
    raster.touch()  # must exist for sidecar_path resolution

    sample_rat.to_file(raster, backend=Backend.vat_dbf)

    dbf_path = tmp_path / "landcover.tif.vat.dbf"
    assert dbf_path.exists(), ".vat.dbf not created"

    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)
    assert rat2.row_count == 4
    assert rat2.column_count == 4


def test_vat_dbf_integer_values(tmp_path, sample_rat):
    raster = tmp_path / "lc.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.vat_dbf)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)
    assert rat2.get_column("Value").values == [1, 2, 3, 4]
    assert rat2.get_column("Count").values == [1000, 5000, 2500, 750]


def test_vat_dbf_string_values(tmp_path, sample_rat):
    raster = tmp_path / "lc.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.vat_dbf)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)
    names = rat2.get_column("ClassName").values
    assert names == ["Water", "Forest", "Urban", "Bare"]


def test_vat_dbf_real_roundtrip(tmp_path, sample_rat):
    raster = tmp_path / "lc.tif"
    raster.touch()
    sample_rat.to_file(raster, backend=Backend.vat_dbf)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)
    albedo = rat2.get_column("Albedo").values
    assert len(albedo) == 4
    assert abs(albedo[0] - 0.08) < 0.01


def test_vat_dbf_many_classes(tmp_path):
    n = 200
    rat = RasterAttributeTable()
    rat.add_column("Value", "Integer", "Generic", values=list(range(n)))
    rat.add_column("ClassName", "String", "Name", values=[f"Class_{i}" for i in range(n)])
    raster = tmp_path / "big.tif"
    raster.touch()
    rat.to_file(raster, backend=Backend.vat_dbf)
    rat2 = RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)
    assert rat2.row_count == n


def test_vat_dbf_missing_raises(tmp_path):
    raster = tmp_path / "no_dbf.tif"
    raster.touch()
    with pytest.raises(FileNotFoundError):
        RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)
