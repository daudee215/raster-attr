"""Benchmark: read/write RAT on a large synthetic categorical raster.

Run with:
    uv run pytest benchmarks/bench_rat.py --benchmark-only -v

The benchmark generates a 100M-pixel categorical raster with 50 000 unique
classes to stress-test the .aux.xml and .vat.dbf backends.
"""

from __future__ import annotations

import random

import pytest

from raster_attr import RasterAttributeTable
from raster_attr.backends import Backend

N_CLASSES = 50_000


@pytest.fixture(scope="module")
def large_rat():
    rat = RasterAttributeTable()
    rat.add_column("Value",     "Integer", "Generic",    values=list(range(N_CLASSES)))
    rat.add_column("Count",     "Integer", "PixelCount", values=[random.randint(1, 10_000) for _ in range(N_CLASSES)])
    rat.add_column("ClassName", "String",  "Name",       values=[f"Class_{i:05d}" for i in range(N_CLASSES)])
    rat.add_column("MeanRefl",  "Real",    "Mean",       values=[round(random.uniform(0.0, 1.0), 4) for _ in range(N_CLASSES)])
    return rat


def test_bench_aux_xml_write(benchmark, large_rat, tmp_path):
    raster = tmp_path / "large.tif"
    raster.touch()

    def _write():
        large_rat.to_file(raster, backend=Backend.aux_xml)

    benchmark(_write)


def test_bench_aux_xml_read(benchmark, large_rat, tmp_path):
    raster = tmp_path / "large.tif"
    raster.touch()
    large_rat.to_file(raster, backend=Backend.aux_xml)

    def _read():
        return RasterAttributeTable.from_file(raster, backend=Backend.aux_xml)

    result = benchmark(_read)
    assert result.row_count == N_CLASSES


def test_bench_vat_dbf_write(benchmark, large_rat, tmp_path):
    raster = tmp_path / "large_dbf.tif"
    raster.touch()

    def _write():
        large_rat.to_file(raster, backend=Backend.vat_dbf)

    benchmark(_write)


def test_bench_vat_dbf_read(benchmark, large_rat, tmp_path):
    raster = tmp_path / "large_dbf.tif"
    raster.touch()
    large_rat.to_file(raster, backend=Backend.vat_dbf)

    def _read():
        return RasterAttributeTable.from_file(raster, backend=Backend.vat_dbf)

    result = benchmark(_read)
    assert result.row_count == N_CLASSES


def test_bench_to_dataframe(benchmark, large_rat):
    benchmark(large_rat.to_dataframe)


def test_bench_from_dataframe(benchmark, large_rat):
    df = large_rat.to_dataframe()
    benchmark(lambda: RasterAttributeTable.from_dataframe(df))
