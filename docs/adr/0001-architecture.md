# ADR-0001: Multi-Backend Architecture for Raster Attribute Table I/O

**Status:** Accepted  
**Date:** 2026-05-16  
**Author:** Daud Tasleem

---

## Context

Raster Attribute Tables (RATs) are stored in at least three incompatible formats depending on the tool that created the raster:

1. **GeoTIFF internal PAM** — GDAL's default. The RAT is written as TIFF internal metadata using the `GDALDefaultRasterAttributeTable` mechanism. Requires GDAL write access to the file.
2. **`.aux.xml` PAM sidecar** — GDAL's fallback when the file is read-only. An XML document whose schema is `GDALRasterAttributeTable > FieldDefn + Row > F` elements.
3. **`.vat.dbf` dBASE III sidecar** — Esri's format. Every NLCD, ESA WorldCover, and USGS raster dataset ships with this file. No Python library read or write it correctly and completely as of 2026-05.

The design challenge: a single Python API must transparently handle all three without requiring the user to know which format is present.

---

## Decision

**Auto-detect the backend from sidecar presence; expose explicit `backend=` parameter for override.**

Detection order:
1. If `<raster>.vat.dbf` exists → `vat_dbf`
2. If `<raster>.aux.xml` exists → `aux_xml`
3. Otherwise → `tiff` (GDAL internal)

This order matches practical precedence: `.vat.dbf` is most commonly the Esri-distributed companion; `.aux.xml` is the GDAL-generated sidecar; TIFF internal is the modern write target.

---

## Alternatives considered

### Alternative A: GDAL-only (tiff backend only)

Use only `osgeo.gdal.RasterAttributeTable` and the GDAL Python bindings.

**Rejected because:**
- Only covers the TIFF internal backend. Completely ignores `.aux.xml` and `.vat.dbf`.
- The GDAL Python API for RATs is a thin, poorly-documented wrapper with no pandas integration.
- Fails silently when GDAL cannot open a read-only file for update.
- Does not help users who receive `.vat.dbf` files from Esri tools or NLCD distributions.

### Alternative B: GDAL VRT + translate pipeline

Use `gdal.Translate()` or `gdal_translate` subprocess to convert formats, then read back.

**Rejected because:**
- Requires a subprocess round-trip with a temporary file, making the API stateful and hard to test.
- `gdal_translate` does not preserve all RAT column types and usages across format boundaries.
- Adds a dependency on the GDAL command-line tools (separate from the Python bindings).

### Alternative C: Direct libtiff tag manipulation for the TIFF backend

Parse GeoTIFF TIFF tags manually using the `tifffile` Python library to read/write the internal PAM metadata.

**Rejected because:**
- GDAL's internal RAT tag layout is not formally documented and has changed across GDAL major versions.
- `tifffile` does not support GDAL's custom private IFD entries for RAT data.
- Maintenance burden is high: any GDAL version bump could silently corrupt the output.
- Using GDAL's own API for GDAL-generated files is the correct approach.

---

## Consequences

- The library has a soft dependency on GDAL Python bindings for the `tiff` backend only. The `aux_xml` and `vat_dbf` backends work without GDAL (useful in environments where GDAL is not installed).
- The auto-detection order must be clearly documented; a user who has both a `.vat.dbf` and a `.aux.xml` will always get `.vat.dbf`.
- Cross-backend conversion (e.g. `.aux.xml` → `.vat.dbf`) is a first-class use case and is tested in the integration suite.
