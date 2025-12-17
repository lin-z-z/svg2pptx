#!/usr/bin/env python3
"""
Batch SVG to PowerPoint Converter

This script converts all SVG files in a folder to PowerPoint presentations.
Each SVG file is converted to a PPTX with the same name.

Usage:
    python batch_convert.py /path/to/folder
    python batch_convert.py /path/to/folder --recursive
    python batch_convert.py /path/to/folder --output /path/to/output
"""

import argparse
import sys
from pathlib import Path

from svg2pptx import svg_to_pptx, Config


def find_svg_files(folder: Path, recursive: bool = False) -> list[Path]:
    """Find all SVG files in a folder."""
    if recursive:
        return list(folder.rglob("*.svg"))
    else:
        return list(folder.glob("*.svg"))


def convert_folder(
    input_folder: Path,
    output_folder: Path = None,
    recursive: bool = False,
    config: Config = None,
) -> tuple[int, int]:
    """
    Convert all SVG files in a folder to PowerPoint.

    Args:
        input_folder: Folder containing SVG files.
        output_folder: Output folder for PPTX files. If None, uses same folder as each SVG.
        recursive: Whether to search subfolders.
        config: Optional conversion configuration.

    Returns:
        Tuple of (success_count, error_count).
    """
    svg_files = find_svg_files(input_folder, recursive)
    
    if not svg_files:
        print(f"No SVG files found in {input_folder}")
        return 0, 0

    print(f"Found {len(svg_files)} SVG file(s)")
    print("-" * 50)

    success_count = 0
    error_count = 0

    for svg_path in svg_files:
        # Determine output path
        if output_folder:
            # Preserve relative structure if recursive
            if recursive:
                relative = svg_path.relative_to(input_folder)
                pptx_path = output_folder / relative.with_suffix(".pptx")
                pptx_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                pptx_path = output_folder / svg_path.with_suffix(".pptx").name
        else:
            # Same folder as the SVG
            pptx_path = svg_path.with_suffix(".pptx")

        try:
            svg_to_pptx(str(svg_path), str(pptx_path), config=config)
            print(f"✓ {svg_path.name} → {pptx_path.name}")
            success_count += 1
        except Exception as e:
            print(f"✗ {svg_path.name}: {e}")
            error_count += 1

    print("-" * 50)
    print(f"Completed: {success_count} success, {error_count} errors")

    return success_count, error_count


def main():
    parser = argparse.ArgumentParser(
        description="Convert all SVG files in a folder to PowerPoint presentations."
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Folder containing SVG files",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output folder for PPTX files (default: same as input)",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Search subfolders recursively",
    )
    parser.add_argument(
        "-s", "--scale",
        type=float,
        default=1.0,
        help="Scale factor for SVG content (default: 1.0)",
    )
    parser.add_argument(
        "-t", "--tolerance",
        type=float,
        default=1.0,
        help="Curve approximation tolerance (default: 1.0)",
    )

    args = parser.parse_args()

    # Validate input folder
    if not args.folder.exists():
        print(f"Error: Folder not found: {args.folder}")
        sys.exit(1)

    if not args.folder.is_dir():
        print(f"Error: Not a folder: {args.folder}")
        sys.exit(1)

    # Create output folder if specified
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)

    # Create config
    config = Config(
        scale=args.scale,
        curve_tolerance=args.tolerance,
    )

    print(f"Converting SVG files in: {args.folder}")
    if args.output:
        print(f"Output folder: {args.output}")
    if args.recursive:
        print("Mode: Recursive")
    print()

    # Convert
    success, errors = convert_folder(
        args.folder,
        args.output,
        args.recursive,
        config,
    )

    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
