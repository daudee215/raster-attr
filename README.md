# raster-attr

**Read, write, and manipulate Raster Attribute Tables (RATs) in Python.**

Raster Attribute Tables store per-class metadata for categorical rasters — land cover, soil type, vegetation class, habitat maps. Every major GIS format supports them, but Python has had no clean, tested library for working with them across all storage backends. This tool fills that gap.

[![PyPI](https://img.shields.io/pypi/v/raster-attr)](https://pypi.org/project/raster-attr/)
[![CI](https://github.com/daudee215/raster-attr/actions/workflows/ci.yml/badge.svg)](https://github.com/daudee215/raster-attr/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org)

---

## Why this exists

GDAL has had RAT support for over a decade, but Python users repeatedly hit the same wall:

- **rasterio has no RAT support** — feature request open since 2024: [rasterio#3185](https://github.com/rasterio/rasterio/issues/3185)
- **InVEST cannot display RATs for LULC maps** — [natcap/invest#2333](https://github.com/natcap/invest/issues/2333)
- **GIS Stack Exchange has multiple unanswered questions** on building and reading RATs with Python/GDAL: [SE#48264](https://gis.stackexchange.com/questions/48264), [SE#55292](https://gis.stackexchange.com/questions/55292), [SE#192356](https://gis.stackexchange.com/questions/192356), [SE#500270](https://gis.stackexchange.com/questions/500270)

The raw GDAL Python bindings (`osgeo.gdal.RasterAttributeTable`) only cover the GeoTIFF internal-metadata backend and have no pandas integration, no CLI, and poor documentation. The `.vat.dbf` format used by Esri and distributed with NLCD/ESA datasets is entirely absent. No maintained PyPI package existed for any of these formats.

`raster-attr` implements all three backends in one library.

---

## What it does

- **Read RATs** from three storage backends automatically detected at runtime:
  - GeoTIFF internal TIFF metadata (GDAL PAM)
  - `.aux.xml` PAM sidecar files
  - `.vat.dbf` dBASE III sidecar files (Esri format)
- **Write RATs** back to any backend, including cross-backend conversion.
- **pandas integration**: `to_dataframe()` / `from_dataframe()` with correct dtypes.
- **CLI**: `raster-attr info`, `raster-attr dump --format csv`, `raster-attr write`.
- **Typed columns** with semantic usage metadata (`PixelCount`, `Name`, `Min`, `Max`, `ColorEntry`, etc.) that downstream tools use for rendering.

---

## Install

```bash
pip install raster-attr
```

GDAL must be installed separately (system package or conda):

```bash
conda install -c conda-forge gdal
# or
sudo apt-get install gdal-bin python3-gdal
```

---

## Quickstart

```python
from raster_attr import RasterAttributeTable

# Read — backend auto-detected from sidecar presence
rat = RasterAttributeTable.from_file("nlcd_2021.tif")
df = rat.to_dataframe()
print(df.head())
#    Value    Count         ClassName  Red  Green  Blue
# 0     11  5200000        Open Water   70    107   159
# 1     21   980000  Developed, Open  222    197   197
# ...

# Modify
rat.add_column("Area_km2", "Real", "Generic",
               values=[v * 900 / 1e6 for v in df["Count"]])  # 30m pixels → km²

# Write back (updates the GeoTIFF in-place)
rat.to_file("nlcd_2021.tif", backend="tiff")

# Convert from .aux.xml to .vat.dbf for ArcGIS compatibility
rat.to_file("nlcd_2021.tif", backend="vat_dbf")

# Build from scratch
rat2 = RasterAttributeTable()
rat2.add_column("Value",     "Integer", "Generic",    values=[1, 2, 3])
rat2.add_column("ClassName", "String",  "Name",       values=["Water", "Forest", "Urban"])
rat2.add_column("Count",     "Integer", "PixelCount", values=[120000, 540000, 89000])
rat2.to_file("mymap.tif")
```

### CLI

```bash
# Inspect column structure
raster-attr info nlcd_2021.tif

# Dump to CSV
raster-attr dump nlcd_2021.tif --format csv > rat.csv

# Dump to JSON
raster-attr dump nlcd_2021.tif --format json

# Write a CSV as a RAT
raster-attr write mymap.tif classes.csv --backend aux_xml
```

---

## API reference

Full API docs at [daudee215.github.io/raster-attr](https://daudee215.github.io/raster-attr).

### `RasterAttributeTable`

| Method | Description |
|---|---|
| `from_file(path, band=1, backend="auto")` | Read a RAT from a raster file. |
| `to_file(path, band=1, backend="auto")` | Write the RAT to a raster file. |
| `to_dataframe()` | Return as a `pandas.DataFrame`. |
| `from_dataframe(df, usages=None)` | Construct from a DataFrame. |
| `add_column(name, col_type, usage, values=None)` | Add a typed column. |
| `remove_column(name)` | Remove a column. |
| `get_column(name)` | Return a `RatColumn` by name. |
| `copy()` | Deep copy. |

### `Backend`

| Value | Description |
|---|---|
| `"auto"` | Detect from sidecar presence (default). |
| `"tiff"` | GeoTIFF internal TIFF metadata via GDAL. |
| `"aux_xml"` | `.aux.xml` PAM sidecar file. |
| `"vat_dbf"` | `.vat.dbf` dBASE III sidecar (Esri). |

---

## Benchmark

Synthetic categorical raster: **50 000 unique classes**, 4 columns (Integer, Integer, String, Real).

| Operation | Backend | Mean time |
|---|---|---|
| Write | `aux_xml` | ~2.1 s |
| Read  | `aux_xml` | ~1.4 s |
| Write | `vat_dbf` | ~0.35 s |
| Read  | `vat_dbf` | ~0.28 s |
| `to_dataframe()` | — | ~0.06 s |
| `from_dataframe()` | — | ~0.08 s |

Benchmarks run on a single core, 2.4 GHz, Python 3.12, `pytest-benchmark`.

---

## Limitations

- The `tiff` backend requires GDAL with write access to the raster file.
- The `.vat.dbf` writer uses dBASE III format; field names are truncated to 10 characters.
- Column name collisions are not resolved automatically on import.
- No support for multi-band RAT selection beyond the `band` parameter.

---

## Citation

```bibtex
@software{tasleem2026rasterattr,
  author    = {Tasleem, Daud},
  title     = {raster-attr: Raster Attribute Table read/write for Python},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/daudee215/raster-attr},
  version   = {0.1.0}
}
```

---

## License

MIT — see [LICENSE](LICENSE).
