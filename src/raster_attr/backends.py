"""Backend detection and routing for RAT storage formats.

Three backends are supported:

``tiff``
    RATs embedded in the GeoTIFF / TIFF file via GDAL's internal PAM
    (Persistent Auxiliary Metadata) mechanism.  This is the standard
    modern format and is what GDAL writes by default.

``aux_xml``
    PAM sidecar file ``<raster>.aux.xml``.  Used by GDAL when the TIFF
    is read-only, and by tools that prefer to keep metadata out of the
    main file.

``vat_dbf``
    Esri's legacy format: a dBASE III file named
    ``<raster>.vat.dbf`` sitting next to the raster.  Many land-cover
    datasets distributed by USGS and ESA include this file to maximise
    ArcGIS compatibility.
"""

from __future__ import annotations

import enum
from pathlib import Path


class Backend(str, enum.Enum):
    """Storage backend selector."""

    tiff = "tiff"
    aux_xml = "aux_xml"
    vat_dbf = "vat_dbf"
    auto = "auto"


def detect_backend(path: str | Path) -> Backend:
    """Infer the most appropriate backend for *path*.

    Detection order
    ---------------
    1. If a ``.vat.dbf`` sidecar exists, return :attr:`Backend.vat_dbf`.
    2. If an ``.aux.xml`` sidecar exists, return :attr:`Backend.aux_xml`.
    3. Otherwise assume :attr:`Backend.tiff` (GDAL will create an internal
       PAM entry if the file is writable, or an ``.aux.xml`` if it is not).

    Parameters
    ----------
    path:
        Path to the raster file.

    Returns
    -------
    Backend
        The detected backend.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.

    Examples
    --------
    >>> detect_backend("nlcd_2021.tif")  # doctest: +SKIP
    <Backend.tiff: 'tiff'>
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Raster not found: {path}")

    vat = p.with_suffix(p.suffix + ".vat.dbf")
    aux = p.with_suffix(p.suffix + ".aux.xml")

    if vat.exists():
        return Backend.vat_dbf
    if aux.exists():
        return Backend.aux_xml
    return Backend.tiff


def sidecar_path(raster_path: str | Path, backend: Backend) -> Path:
    """Return the expected sidecar file path for the given backend.

    Parameters
    ----------
    raster_path:
        Path to the raster file.
    backend:
        The backend whose sidecar path is requested.

    Returns
    -------
    Path
        The sidecar path.  For :attr:`Backend.tiff` this returns the
        raster path itself (the RAT lives inside the file).
    """
    p = Path(raster_path)
    if backend == Backend.tiff:
        return p
    if backend == Backend.aux_xml:
        return p.with_suffix(p.suffix + ".aux.xml")
    if backend == Backend.vat_dbf:
        return p.with_suffix(p.suffix + ".vat.dbf")
    raise ValueError(f"Cannot resolve sidecar for backend: {backend}")
