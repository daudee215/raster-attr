"""raster-attr: Read, write, and manipulate Raster Attribute Tables (RATs).

Supports three backends:
- GeoTIFF internal TIFF metadata (via GDAL RAT API)
- .aux.xml PAM sidecar files
- .vat.dbf dBASE III files (Esri compatibility)

Quick start::

    from raster_attr import RasterAttributeTable
    rat = RasterAttributeTable.from_file("landcover.tif")
    df = rat.to_dataframe()
    rat.add_column("Area_km2", col_type="Real", usage="Generic")
    rat.to_file("landcover_updated.tif")
"""

from raster_attr.backends import Backend
from raster_attr.column import ColType, ColUsage, RatColumn
from raster_attr.rat import RasterAttributeTable

__version__ = "0.1.0"
__all__ = ["RasterAttributeTable", "RatColumn", "ColType", "ColUsage", "Backend"]
