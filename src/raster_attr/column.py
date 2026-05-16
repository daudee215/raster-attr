"""Column type and usage enumerations for Raster Attribute Tables."""

from __future__ import annotations

from enum import Enum


class ColType(str, Enum):
    """Data type for a RAT column.

    Matches GDAL's GDALRATFieldType enumeration.
    """
    Integer = "Integer"
    Real = "Real"
    String = "String"


class ColUsage(str, Enum):
    """Semantic usage for a RAT column.

    Matches GDAL's GDALRATFieldUsage enumeration.  GDAL uses these to
    drive rendering (e.g. PixelCount drives histogram display, ColorEntry
    columns are used to build a colour table).
    """
    Generic = "Generic"
    PixelCount = "PixelCount"
    Name = "Name"
    Min = "Min"
    Max = "Max"
    Mean = "Mean"
    StdDev = "StdDev"
    ColorMin = "ColorMin"
    ColorMax = "ColorMax"
    ColorMean = "ColorMean"
    ColorStdDev = "ColorStdDev"
    ColorEntry = "ColorEntry"
    Histogram = "Histogram"
    MinMax = "MinMax"


class RatColumn:
    """Metadata descriptor for a single RAT column.

    Parameters
    ----------
    name:
        Column name exactly as stored in the file.
    col_type:
        Data type.
    usage:
        Semantic usage that GDAL and downstream tools use for rendering.
    values:
        The actual column data as a plain Python list.  Length must equal the
        number of rows in the parent :class:`RasterAttributeTable`.

    Examples
    --------
    >>> col = RatColumn("ClassName", ColType.String, ColUsage.Name, ["Water", "Forest"])
    >>> col.values[0]
    'Water'
    """

    def __init__(
        self,
        name: str,
        col_type: ColType | str,
        usage: ColUsage | str,
        values: list[int | float | str] | None = None,
    ) -> None:
        self.name = name
        self.col_type = ColType(col_type)
        self.usage = ColUsage(usage)
        self.values: list[int | float | str] = values if values is not None else []

    def __repr__(self) -> str:
        return (
            f"RatColumn(name={self.name!r}, col_type={self.col_type.value!r}, "
            f"usage={self.usage.value!r}, rows={len(self.values)})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RatColumn):
            return NotImplemented
        return (
            self.name == other.name
            and self.col_type == other.col_type
            and self.usage == other.usage
            and self.values == other.values
        )
