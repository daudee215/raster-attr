"""Command-line interface for raster-attr."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from raster_attr import RasterAttributeTable
from raster_attr.backends import Backend


def _cmd_info(args: argparse.Namespace) -> int:
    rat = RasterAttributeTable.from_file(args.path, band=args.band, backend=args.backend)
    print(f"File   : {args.path}")
    print(f"Rows   : {rat.row_count}")
    print(f"Columns: {rat.column_count}")
    for col in rat._columns:
        print(f"  {col.name:<20} type={col.col_type.value:<10} usage={col.usage.value}")
    return 0


def _cmd_dump(args: argparse.Namespace) -> int:
    rat = RasterAttributeTable.from_file(args.path, band=args.band, backend=args.backend)
    df = rat.to_dataframe()
    if args.format == "csv":
        print(df.to_csv(index=False))
    else:
        print(df.to_json(orient="records", indent=2))
    return 0


def _cmd_write(args: argparse.Namespace) -> int:
    import pandas as pd
    df = pd.read_csv(args.csv)
    from raster_attr import RasterAttributeTable as RAT
    rat = RAT.from_dataframe(df)
    rat.to_file(args.path, band=args.band, backend=args.backend)
    print(f"RAT written to {args.path} ({args.backend} backend)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="raster-attr",
        description="Read, write, and inspect Raster Attribute Tables (RATs).",
    )
    parser.add_argument("--band", type=int, default=1, help="1-based band index (default: 1)")
    parser.add_argument(
        "--backend",
        choices=["auto", "tiff", "aux_xml", "vat_dbf"],
        default="auto",
        help="Storage backend (default: auto-detect)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Print RAT column summary.")
    p_info.add_argument("path", help="Raster file path.")

    p_dump = sub.add_parser("dump", help="Dump RAT to CSV or JSON.")
    p_dump.add_argument("path", help="Raster file path.")
    p_dump.add_argument(
        "--format", choices=["csv", "json"], default="csv", help="Output format."
    )

    p_write = sub.add_parser("write", help="Write a CSV as RAT into a raster.")
    p_write.add_argument("path", help="Raster file path (must exist).")
    p_write.add_argument("csv", help="Input CSV with one row per class.")

    args = parser.parse_args(argv)
    try:
        if args.command == "info":
            return _cmd_info(args)
        if args.command == "dump":
            return _cmd_dump(args)
        if args.command == "write":
            return _cmd_write(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
