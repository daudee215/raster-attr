"""Core RasterAttributeTable class with multi-backend read/write."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np
import pandas as pd

from raster_attr.column import ColType, ColUsage, RatColumn
from raster_attr.backends import Backend, detect_backend, sidecar_path

if TYPE_CHECKING:
    pass

# GDAL import — optional at module level so tests can mock it
try:
    from osgeo import gdal
    gdal.UseExceptions()
    _HAS_GDAL = True
except ImportError:
    _HAS_GDAL = False

_GDAL_TYPE_MAP: dict[ColType, int] = {}
_GDAL_USAGE_MAP: dict[ColUsage, int] = {}


def _ensure_gdal() -> None:
    if not _HAS_GDAL:
        raise ImportError(
            "GDAL Python bindings are required. "
            "Install with: pip install GDAL or conda install -c conda-forge gdal"
        )
    global _GDAL_TYPE_MAP, _GDAL_USAGE_MAP
    if not _GDAL_TYPE_MAP:
        _GDAL_TYPE_MAP = {
            ColType.Integer: gdal.GFT_Integer,
            ColType.Real: gdal.GFT_Real,
            ColType.String: gdal.GFT_String,
        }
        _GDAL_USAGE_MAP = {
            ColUsage.Generic: gdal.GFU_Generic,
            ColUsage.PixelCount: gdal.GFU_PixelCount,
            ColUsage.Name: gdal.GFU_Name,
            ColUsage.Min: gdal.GFU_Min,
            ColUsage.Max: gdal.GFU_Max,
            ColUsage.Mean: gdal.GFU_Mean,
            ColUsage.StdDev: gdal.GFU_StdDev,
            ColUsage.ColorMin: gdal.GFU_Alpha,  # fallback
            ColUsage.ColorMax: gdal.GFU_Alpha,
            ColUsage.ColorMean: gdal.GFU_Alpha,
            ColUsage.ColorStdDev: gdal.GFU_Alpha,
            ColUsage.ColorEntry: gdal.GFU_Alpha,
            ColUsage.Histogram: gdal.GFU_PixelCount,
            ColUsage.MinMax: gdal.GFU_MinMax,
        }


class RasterAttributeTable:
    """A Raster Attribute Table with multi-backend support.

    A RAT is a typed-column table that stores per-class metadata for a
    categorical raster (e.g. land cover, soil type, vegetation class).
    Each row corresponds to one unique pixel value (class) in the raster.

    This class reads from and writes to three backends:

    * ``tiff`` — GDAL internal PAM metadata embedded in the GeoTIFF
    * ``aux_xml`` — ``.aux.xml`` PAM sidecar file
    * ``vat_dbf`` — Esri ``.vat.dbf`` dBASE III sidecar file

    Parameters
    ----------
    columns:
        Ordered list of :class:`~raster_attr.column.RatColumn` objects.
    row_count:
        Number of rows (classes) in the table.  Must equal
        ``len(col.values)`` for every column.

    Examples
    --------
    Read a RAT from a GeoTIFF:

    >>> from raster_attr import RasterAttributeTable
    >>> rat = RasterAttributeTable.from_file("landcover.tif")
    >>> df = rat.to_dataframe()
    >>> print(df.head())

    Create a RAT from scratch and write it:

    >>> rat = RasterAttributeTable()
    >>> rat.add_column("Value", "Integer", "Generic", values=[1, 2, 3])
    >>> rat.add_column("ClassName", "String", "Name", values=["Water", "Forest", "Urban"])
    >>> rat.to_file("landcover.tif")
    """

    def __init__(
        self,
        columns: list[RatColumn] | None = None,
        row_count: int = 0,
    ) -> None:
        self._columns: list[RatColumn] = columns if columns is not None else []
        self._row_count: int = row_count
        if self._columns and self._row_count == 0:
            self._row_count = max((len(c.values) for c in self._columns), default=0)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def row_count(self) -> int:
        """Number of rows (classes) in the table."""
        return self._row_count

    @property
    def column_count(self) -> int:
        """Number of columns."""
        return len(self._columns)

    @property
    def column_names(self) -> list[str]:
        """Ordered list of column names."""
        return [c.name for c in self._columns]

    # ------------------------------------------------------------------
    # Column operations
    # ------------------------------------------------------------------

    def add_column(
        self,
        name: str,
        col_type: ColType | str,
        usage: ColUsage | str,
        values: list[int | float | str] | None = None,
    ) -> None:
        """Add a column to the table.

        Parameters
        ----------
        name:
            Column name.
        col_type:
            Data type (``'Integer'``, ``'Real'``, or ``'String'``).
        usage:
            Semantic usage for GDAL rendering.
        values:
            Per-row values.  If the table already has rows, *values* must
            have exactly :attr:`row_count` elements.  Pass ``None`` to
            fill with zeros / empty strings.

        Raises
        ------
        ValueError
            If *values* length does not match :attr:`row_count`.
        """
        col_type = ColType(col_type)
        usage = ColUsage(usage)
        if values is None:
            default: int | float | str = 0 if col_type != ColType.String else ""
            values = [default] * self._row_count
        if self._row_count and len(values) != self._row_count:
            raise ValueError(
                f"Column '{name}' has {len(values)} values but table has {self._row_count} rows."
            )
        if not self._row_count:
            self._row_count = len(values)
        self._columns.append(RatColumn(name, col_type, usage, list(values)))

    def remove_column(self, name: str) -> None:
        """Remove a column by name.

        Raises
        ------
        KeyError
            If the column does not exist.
        """
        for i, col in enumerate(self._columns):
            if col.name == name:
                self._columns.pop(i)
                return
        raise KeyError(f"Column not found: {name!r}")

    def get_column(self, name: str) -> RatColumn:
        """Return a column by name.

        Raises
        ------
        KeyError
            If the column does not exist.
        """
        for col in self._columns:
            if col.name == name:
                return col
        raise KeyError(f"Column not found: {name!r}")

    # ------------------------------------------------------------------
    # DataFrame conversion
    # ------------------------------------------------------------------

    def to_dataframe(self) -> pd.DataFrame:
        """Return the RAT as a :class:`pandas.DataFrame`.

        Column dtypes follow the RAT column type:
        ``Integer`` → ``int64``, ``Real`` → ``float64``,
        ``String`` → ``object``.

        Returns
        -------
        pandas.DataFrame
            One row per class, one column per RAT column.
        """
        data: dict[str, Any] = {}
        for col in self._columns:
            if col.col_type == ColType.Integer:
                data[col.name] = pd.array(col.values, dtype="int64")
            elif col.col_type == ColType.Real:
                data[col.name] = pd.array(col.values, dtype="float64")
            else:
                data[col.name] = col.values
        return pd.DataFrame(data)

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        usages: dict[str, ColUsage | str] | None = None,
    ) -> "RasterAttributeTable":
        """Construct a RAT from a :class:`pandas.DataFrame`.

        Parameters
        ----------
        df:
            Source DataFrame.  Column names become RAT column names.
        usages:
            Optional mapping from column name to :class:`~raster_attr.column.ColUsage`.
            Columns not listed default to :attr:`~raster_attr.column.ColUsage.Generic`.

        Returns
        -------
        RasterAttributeTable
        """
        usages = usages or {}
        rat = cls()
        for col_name in df.columns:
            dtype = df[col_name].dtype
            if pd.api.types.is_integer_dtype(dtype):
                col_type = ColType.Integer
            elif pd.api.types.is_float_dtype(dtype):
                col_type = ColType.Real
            else:
                col_type = ColType.String
            usage = ColUsage(usages.get(col_name, ColUsage.Generic))
            rat.add_column(col_name, col_type, usage, values=df[col_name].tolist())
        return rat

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        band: int = 1,
        backend: Backend | str = Backend.auto,
    ) -> "RasterAttributeTable":
        """Read a RAT from a raster file.

        Parameters
        ----------
        path:
            Path to the raster file.
        band:
            1-based band index (default: 1).
        backend:
            Storage backend.  Use :attr:`~raster_attr.backends.Backend.auto`
            (default) to detect automatically.

        Returns
        -------
        RasterAttributeTable

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        ValueError
            If the band has no RAT.
        """
        backend = Backend(backend)
        if backend == Backend.auto:
            backend = detect_backend(path)

        if backend == Backend.vat_dbf:
            return cls._read_vat_dbf(path)
        if backend == Backend.aux_xml:
            return cls._read_aux_xml(path)
        return cls._read_tiff(path, band)

    def to_file(
        self,
        path: str | Path,
        band: int = 1,
        backend: Backend | str = Backend.auto,
    ) -> None:
        """Write the RAT to a raster file.

        For the ``tiff`` backend, the raster must already exist and be
        writable.  For ``aux_xml`` and ``vat_dbf``, sidecar files are
        created or overwritten next to the raster.

        Parameters
        ----------
        path:
            Path to the raster file.
        band:
            1-based band index (default: 1).
        backend:
            Storage backend.  :attr:`~raster_attr.backends.Backend.auto`
            writes to ``tiff`` if the file is writable, else ``aux_xml``.
        """
        backend = Backend(backend)
        if backend == Backend.auto:
            backend = Backend.tiff if os.access(path, os.W_OK) else Backend.aux_xml

        if backend == Backend.vat_dbf:
            self._write_vat_dbf(path)
        elif backend == Backend.aux_xml:
            self._write_aux_xml(path)
        else:
            self._write_tiff(path, band)

    # ------------------------------------------------------------------
    # TIFF backend
    # ------------------------------------------------------------------

    @classmethod
    def _read_tiff(cls, path: str | Path, band: int) -> "RasterAttributeTable":
        _ensure_gdal()
        ds = gdal.Open(str(path))
        if ds is None:
            raise FileNotFoundError(f"GDAL could not open: {path}")
        rb = ds.GetRasterBand(band)
        gdal_rat = rb.GetDefaultRAT()
        if gdal_rat is None:
            ds = None
            raise ValueError(f"Band {band} of {path!r} has no Raster Attribute Table.")

        _type_reverse = {v: k for k, v in {
            ColType.Integer: gdal.GFT_Integer,
            ColType.Real: gdal.GFT_Real,
            ColType.String: gdal.GFT_String,
        }.items()}
        _usage_reverse = {
            gdal.GFU_Generic: ColUsage.Generic,
            gdal.GFU_PixelCount: ColUsage.PixelCount,
            gdal.GFU_Name: ColUsage.Name,
            gdal.GFU_Min: ColUsage.Min,
            gdal.GFU_Max: ColUsage.Max,
            gdal.GFU_Mean: ColUsage.Mean,
            gdal.GFU_StdDev: ColUsage.StdDev,
            gdal.GFU_MinMax: ColUsage.MinMax,
        }

        n_rows = gdal_rat.GetRowCount()
        n_cols = gdal_rat.GetColumnCount()
        columns: list[RatColumn] = []
        for ci in range(n_cols):
            col_name = gdal_rat.GetNameOfCol(ci)
            gdal_type = gdal_rat.GetTypeOfCol(ci)
            gdal_usage = gdal_rat.GetUsageOfCol(ci)
            col_type = _type_reverse.get(gdal_type, ColType.String)
            usage = _usage_reverse.get(gdal_usage, ColUsage.Generic)
            values: list[int | float | str] = []
            for ri in range(n_rows):
                if col_type == ColType.Integer:
                    values.append(gdal_rat.GetValueAsInt(ri, ci))
                elif col_type == ColType.Real:
                    values.append(gdal_rat.GetValueAsDouble(ri, ci))
                else:
                    values.append(gdal_rat.GetValueAsString(ri, ci))
            columns.append(RatColumn(col_name, col_type, usage, values))

        ds = None
        return cls(columns=columns, row_count=n_rows)

    def _write_tiff(self, path: str | Path, band: int) -> None:
        _ensure_gdal()
        _ensure_gdal()
        ds = gdal.Open(str(path), gdal.GA_Update)
        if ds is None:
            raise FileNotFoundError(f"GDAL could not open for update: {path}")
        rb = ds.GetRasterBand(band)
        gdal_rat = gdal.RasterAttributeTable()

        for col in self._columns:
            gdal_type = _GDAL_TYPE_MAP.get(col.col_type, gdal.GFT_String)
            gdal_usage = _GDAL_USAGE_MAP.get(col.usage, gdal.GFU_Generic)
            gdal_rat.CreateColumn(col.name, gdal_type, gdal_usage)

        gdal_rat.SetRowCount(self._row_count)
        for ci, col in enumerate(self._columns):
            for ri, val in enumerate(col.values):
                if col.col_type == ColType.Integer:
                    gdal_rat.SetValueAsInt(ri, ci, int(val))
                elif col.col_type == ColType.Real:
                    gdal_rat.SetValueAsDouble(ri, ci, float(val))
                else:
                    gdal_rat.SetValueAsString(ri, ci, str(val))

        rb.SetDefaultRAT(gdal_rat)
        ds.FlushCache()
        ds = None

    # ------------------------------------------------------------------
    # .aux.xml backend
    # ------------------------------------------------------------------

    @classmethod
    def _read_aux_xml(cls, raster_path: str | Path) -> "RasterAttributeTable":
        from lxml import etree  # type: ignore[import]

        aux_path = sidecar_path(raster_path, Backend.aux_xml)
        if not aux_path.exists():
            raise FileNotFoundError(f".aux.xml not found: {aux_path}")

        tree = etree.parse(str(aux_path))
        root = tree.getroot()
        rat_el = root.find(".//GDALRasterAttributeTable")
        if rat_el is None:
            raise ValueError(f"No GDALRasterAttributeTable in {aux_path}")

        columns: list[RatColumn] = []
        n_rows: int = 0
        for field_el in rat_el.findall("FieldDefn"):
            col_name = field_el.findtext("Name", "")
            col_type = ColType(field_el.findtext("Type", "String"))
            usage = ColUsage(field_el.findtext("Usage", "Generic"))
            values: list[int | float | str] = []
            columns.append(RatColumn(col_name, col_type, usage, values))

        for row_el in rat_el.findall("Row"):
            n_rows += 1
            for ci, f_el in enumerate(row_el.findall("F")):
                val_str = f_el.text or ""
                if ci < len(columns):
                    ct = columns[ci].col_type
                    if ct == ColType.Integer:
                        columns[ci].values.append(int(val_str) if val_str else 0)
                    elif ct == ColType.Real:
                        columns[ci].values.append(float(val_str) if val_str else 0.0)
                    else:
                        columns[ci].values.append(val_str)

        return cls(columns=columns, row_count=n_rows)

    def _write_aux_xml(self, raster_path: str | Path) -> None:
        from lxml import etree  # type: ignore[import]

        aux_path = sidecar_path(raster_path, Backend.aux_xml)
        # Load existing or create fresh root
        if Path(aux_path).exists():
            tree = etree.parse(str(aux_path))
            root = tree.getroot()
            # Remove existing RAT
            for old in root.findall(".//GDALRasterAttributeTable"):
                old.getparent().remove(old)
        else:
            root = etree.Element("PAMDataset")

        # Find or create PAMRasterBand
        band_el = root.find("PAMRasterBand")
        if band_el is None:
            band_el = etree.SubElement(root, "PAMRasterBand")
            band_el.set("band", "1")

        rat_el = etree.SubElement(band_el, "GDALRasterAttributeTable")
        for ci, col in enumerate(self._columns):
            fd = etree.SubElement(rat_el, "FieldDefn")
            fd.set("index", str(ci))
            etree.SubElement(fd, "Name").text = col.name
            etree.SubElement(fd, "Type").text = col.col_type.value
            etree.SubElement(fd, "Usage").text = col.usage.value

        for ri in range(self._row_count):
            row_el = etree.SubElement(rat_el, "Row")
            row_el.set("index", str(ri))
            for col in self._columns:
                f_el = etree.SubElement(row_el, "F")
                f_el.text = str(col.values[ri]) if ri < len(col.values) else ""

        tree = etree.ElementTree(root)
        tree.write(str(aux_path), xml_declaration=True, encoding="utf-8", pretty_print=True)

    # ------------------------------------------------------------------
    # .vat.dbf backend
    # ------------------------------------------------------------------

    @classmethod
    def _read_vat_dbf(cls, raster_path: str | Path) -> "RasterAttributeTable":
        from dbfread import DBF  # type: ignore[import]

        dbf_path = sidecar_path(raster_path, Backend.vat_dbf)
        if not dbf_path.exists():
            raise FileNotFoundError(f".vat.dbf not found: {dbf_path}")

        table = DBF(str(dbf_path), load=True)
        if not table.records:
            return cls()

        # Build columns from first record
        sample = table.records[0]
        columns: list[RatColumn] = []
        for field_name in sample.keys():
            val = sample[field_name]
            if isinstance(val, int):
                ct = ColType.Integer
            elif isinstance(val, float):
                ct = ColType.Real
            else:
                ct = ColType.String
            # Heuristic usage assignment
            fn_lower = field_name.lower()
            if fn_lower in ("value", "pixelvalue"):
                usage = ColUsage.Generic
            elif fn_lower in ("count", "pixelcount"):
                usage = ColUsage.PixelCount
            elif fn_lower in ("classname", "class", "name", "label", "description"):
                usage = ColUsage.Name
            else:
                usage = ColUsage.Generic
            columns.append(RatColumn(field_name, ct, usage, []))

        for rec in table.records:
            for ci, field_name in enumerate(sample.keys()):
                val = rec[field_name]
                ct = columns[ci].col_type
                if ct == ColType.Integer:
                    columns[ci].values.append(int(val) if val is not None else 0)
                elif ct == ColType.Real:
                    columns[ci].values.append(float(val) if val is not None else 0.0)
                else:
                    columns[ci].values.append(str(val) if val is not None else "")

        return cls(columns=columns, row_count=len(table.records))

    def _write_vat_dbf(self, raster_path: str | Path) -> None:
        """Write a ``.vat.dbf`` using the struct-based dBASE III format."""
        import struct, datetime

        dbf_path = sidecar_path(raster_path, Backend.vat_dbf)

        # dBASE III header
        now = datetime.date.today()
        n_records = self._row_count
        header_size = 32 + 32 * len(self._columns) + 1  # +1 terminator

        # Build field descriptors
        field_specs: list[tuple[bytes, bytes, int]] = []
        for col in self._columns:
            name_b = col.name[:10].encode("ascii", errors="replace").ljust(10, b"\x00")
            if col.col_type == ColType.Integer:
                field_specs.append((name_b, b"N", 11))
            elif col.col_type == ColType.Real:
                field_specs.append((name_b, b"N", 18))
            else:
                max_len = max((len(str(v)) for v in col.values), default=1)
                field_specs.append((name_b, b"C", min(max(max_len, 1), 254)))

        record_size = 1 + sum(s for _, _, s in field_specs)  # +1 deletion flag

        with open(str(dbf_path), "wb") as f:
            # 32-byte header
            f.write(struct.pack("B", 3))  # version
            f.write(struct.pack("3B", now.year - 1900, now.month, now.day))
            f.write(struct.pack("<I", n_records))
            f.write(struct.pack("<H", header_size))
            f.write(struct.pack("<H", record_size))
            f.write(b"\x00" * 20)  # reserved

            # Field descriptor records (32 bytes each)
            for name_b, ftype, flen in field_specs:
                f.write(name_b[:10].ljust(10, b"\x00") + b"\x00")  # 11 bytes
                f.write(ftype)  # 1 byte
                f.write(b"\x00" * 4)  # reserved
                f.write(struct.pack("B", flen))  # field length
                f.write(struct.pack("B", 2 if ftype == b"N" else 0))  # decimal count
                f.write(b"\x00" * 14)  # reserved

            f.write(b"\r")  # header terminator

            # Records
            for ri in range(self._row_count):
                f.write(b" ")  # deletion flag (not deleted)
                for ci, (_, ftype, flen) in enumerate(field_specs):
                    col = self._columns[ci]
                    val = col.values[ri] if ri < len(col.values) else ""
                    if ftype == b"N":
                        s = f"{val:{flen}.2f}" if col.col_type == ColType.Real else f"{int(val):{flen}}"
                    else:
                        s = str(val)
                    # Pad / truncate to flen
                    encoded = s.encode("ascii", errors="replace")[:flen].ljust(flen, b" ")
                    f.write(encoded)

            f.write(b"\x1a")  # EOF marker

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return self._row_count

    def __repr__(self) -> str:
        return (
            f"RasterAttributeTable(rows={self._row_count}, "
            f"columns={self.column_names})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RasterAttributeTable):
            return NotImplemented
        return self._row_count == other._row_count and self._columns == other._columns

    def copy(self) -> "RasterAttributeTable":
        """Return a deep copy."""
        return copy.deepcopy(self)
