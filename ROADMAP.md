# Roadmap

## v0.1.0 — Initial release (current)

- Read/write RATs from three backends: GeoTIFF internal, `.aux.xml`, `.vat.dbf`.
- Auto-detect backend from sidecar presence.
- `pandas.DataFrame` round-trip with correct dtypes.
- Typed columns with semantic usage metadata.
- CLI: `info`, `dump`, `write` sub-commands.
- Unit tests, integration tests on bundled NLCD-style sample data.
- Benchmark on 50 000-class synthetic RAT.

## v0.2.0 — Correctness and ecosystem integration

- **NLCD 2021 reference validation**: automated CI test that downloads the public NLCD 2021 GeoTIFF and verifies the RAT round-trip matches the known class table published by USGS.
- **ESA WorldCover `.vat.dbf` compatibility**: verified round-trip on ESA WorldCover 2021 sidecar files.
- **rioxarray bridge**: `RasterAttributeTable.from_xarray()` / `.to_xarray_attrs()` for attaching RAT metadata to xarray DataArrays.
- **Color table extraction**: `to_colormap()` returns a matplotlib-compatible colormap from `ColorEntry`-type columns.
- **Multi-band support**: `from_file(path, band=N)` for files with per-band RATs.
- Python 3.13 support.

## v1.0.0 — Stable API

- Stable, versioned API with deprecation policy.
- Rust-accelerated `.vat.dbf` and `.aux.xml` I/O for files with > 100 000 classes (via PyO3 extension).
- COG-aware TIFF backend that reads/writes RATs without fully loading the raster into memory.
- Integration with `stac-asset` to read RATs from remote COG files on S3/Azure.
- Full GDAL RAT usage enum coverage including `ColorMin`, `ColorMax`, `ColorMean`, `ColorStdDev`.
- Published documentation site.
