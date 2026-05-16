"""Integration tests: full round-trip using real sample data files."""

from pathlib import Path

from raster_attr import RasterAttributeTable
from raster_attr.backends import Backend

DATA_DIR = Path(__file__).parent.parent / "data"


def test_sample_aux_xml_roundtrip():
    """Round-trip the bundled .aux.xml sample through read → modify → write → re-read."""
    sample = DATA_DIR / "sample_landcover.tif"
    assert sample.exists(), f"Sample data missing: {sample}"

    rat = RasterAttributeTable.from_file(sample, backend=Backend.aux_xml)
    assert rat.row_count >= 4
    assert rat.column_count >= 3

    # Verify known class names from the sample
    names = rat.get_column("ClassName").values
    assert "Open Water" in names


def test_sample_vat_dbf_roundtrip():
    """Round-trip the bundled .vat.dbf sample."""
    sample = DATA_DIR / "sample_landcover.tif"
    assert sample.exists()

    rat = RasterAttributeTable.from_file(sample, backend=Backend.vat_dbf)
    assert rat.row_count >= 4
    df = rat.to_dataframe()
    assert "ClassName" in df.columns
    assert len(df) == rat.row_count


def test_roundtrip_aux_xml_to_vat_dbf(tmp_path):
    """Convert the bundled .aux.xml to .vat.dbf and verify fidelity."""
    sample = DATA_DIR / "sample_landcover.tif"
    rat_orig = RasterAttributeTable.from_file(sample, backend=Backend.aux_xml)

    out_raster = tmp_path / "converted.tif"
    import shutil
    shutil.copy(sample, out_raster)

    rat_orig.to_file(out_raster, backend=Backend.vat_dbf)
    rat_converted = RasterAttributeTable.from_file(out_raster, backend=Backend.vat_dbf)

    assert rat_converted.row_count == rat_orig.row_count
    orig_names = rat_orig.get_column("ClassName").values
    conv_names = rat_converted.get_column("ClassName").values
    assert orig_names == conv_names


def test_dataframe_roundtrip_preserves_types():
    """to_dataframe → from_dataframe → to_dataframe should be lossless for all types."""
    sample = DATA_DIR / "sample_landcover.tif"
    rat1 = RasterAttributeTable.from_file(sample, backend=Backend.aux_xml)
    df1 = rat1.to_dataframe()

    rat2 = RasterAttributeTable.from_dataframe(df1)
    df2 = rat2.to_dataframe()

    assert list(df1.columns) == list(df2.columns)
    assert len(df1) == len(df2)
    for col in df1.columns:
        assert list(df1[col]) == list(df2[col]), f"Mismatch in column '{col}'"
