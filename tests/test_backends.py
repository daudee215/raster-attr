"""Unit tests for backend detection logic."""

import os
import tempfile
from pathlib import Path

import pytest

from raster_attr.backends import Backend, detect_backend, sidecar_path


def _touch(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).touch()


def test_detect_backend_tiff(tmp_path):
    raster = tmp_path / "test.tif"
    raster.touch()
    assert detect_backend(raster) == Backend.tiff


def test_detect_backend_aux_xml(tmp_path):
    raster = tmp_path / "test.tif"
    raster.touch()
    (tmp_path / "test.tif.aux.xml").touch()
    assert detect_backend(raster) == Backend.aux_xml


def test_detect_backend_vat_dbf(tmp_path):
    raster = tmp_path / "test.tif"
    raster.touch()
    (tmp_path / "test.tif.vat.dbf").touch()
    assert detect_backend(raster) == Backend.vat_dbf


def test_detect_backend_vat_wins_over_aux(tmp_path):
    """When both .vat.dbf and .aux.xml exist, .vat.dbf takes priority."""
    raster = tmp_path / "test.tif"
    raster.touch()
    (tmp_path / "test.tif.aux.xml").touch()
    (tmp_path / "test.tif.vat.dbf").touch()
    assert detect_backend(raster) == Backend.vat_dbf


def test_detect_backend_not_found():
    with pytest.raises(FileNotFoundError):
        detect_backend("/nonexistent/raster.tif")


def test_sidecar_path_tiff(tmp_path):
    raster = tmp_path / "test.tif"
    assert sidecar_path(raster, Backend.tiff) == raster


def test_sidecar_path_aux_xml(tmp_path):
    raster = tmp_path / "test.tif"
    expected = tmp_path / "test.tif.aux.xml"
    assert sidecar_path(raster, Backend.aux_xml) == expected


def test_sidecar_path_vat_dbf(tmp_path):
    raster = tmp_path / "test.tif"
    expected = tmp_path / "test.tif.vat.dbf"
    assert sidecar_path(raster, Backend.vat_dbf) == expected


def test_sidecar_path_auto_raises(tmp_path):
    with pytest.raises(ValueError):
        sidecar_path(tmp_path / "test.tif", Backend.auto)
