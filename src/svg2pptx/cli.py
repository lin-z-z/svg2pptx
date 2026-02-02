"""Command-line interface for SVG to PowerPoint conversion."""

import argparse
import sys
from pathlib import Path

from svg2pptx import svg_to_pptx, Config, __version__


def convert_single_file(input_path: Path, output_path: Path, config: Config) -> bool:
    """Convert a single SVG file to PPTX.
    
    Returns True on success, False on failure.
    """
    try:
        svg_to_pptx(str(input_path), str(output_path), config=config)
        return True
    except Exception as e:
        print(f"Error converting '{input_path}': {e}", file=sys.stderr)
        return False


def convert_folder(input_dir: Path, output_dir: Path, config: Config, recursive: bool = False) -> tuple[int, int]:
    """Convert all SVG files in a folder to PPTX.
    
    Returns tuple of (success_count, failure_count).
    """
    # Find all SVG files
    if recursive:
        svg_files = list(input_dir.rglob("*.svg"))
    else:
        svg_files = list(input_dir.glob("*.svg"))
    
    if not svg_files:
        print(f"No SVG files found in '{input_dir}'", file=sys.stderr)
        return 0, 0
    
    print(f"Found {len(svg_files)} SVG file(s) to convert...")
    
    success_count = 0
    failure_count = 0
    
    for svg_file in svg_files:
        # Determine output path preserving subdirectory structure for recursive mode
        if recursive:
            relative_path = svg_file.relative_to(input_dir)
            pptx_path = output_dir / relative_path.with_suffix(".pptx")
        else:
            pptx_path = output_dir / svg_file.with_suffix(".pptx").name
        
        # Create output subdirectory if needed
        pptx_path.parent.mkdir(parents=True, exist_ok=True)
        
        if convert_single_file(svg_file, pptx_path, config):
            print(f"  ✓ {svg_file.name} → {pptx_path.name}")
            success_count += 1
        else:
            print(f"  ✗ {svg_file.name} (failed)")
            failure_count += 1
    
    return success_count, failure_count


def main():
    """Main entry point for the svg2pptx CLI."""
    parser = argparse.ArgumentParser(
        prog="svg2pptx",
        description="Convert SVG files to native, editable PowerPoint shapes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file conversion
  svg2pptx input.svg output.pptx
  svg2pptx diagram.svg presentation.pptx --no-text

  # Folder batch conversion
  svg2pptx ./svgs/ ./pptx_output/
  svg2pptx ./icons/ ./converted/ --recursive
  svg2pptx ./assets/ ./assets/  # Convert in-place
        """,
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to the input SVG file or folder containing SVG files",
    )

    parser.add_argument(
        "output",
        type=str,
        help="Path for the output PowerPoint file or output folder (for batch mode)",
    )

    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively convert SVG files in subfolders (batch mode only)",
    )

    parser.add_argument(
        "--no-text",
        action="store_true",
        dest="no_text",
        help="Skip converting text elements",
    )

    parser.add_argument(
        "--no-shapes",
        action="store_true",
        dest="no_shapes",
        help="Skip converting shape elements (rectangles, circles, paths, etc.)",
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor for the SVG content (default: 1.0)",
    )

    parser.add_argument(
        "--flatten",
        action="store_true",
        default=True,
        help="Flatten groups into individual shapes (default: True)",
    )

    parser.add_argument(
        "--no-flatten",
        action="store_false",
        dest="flatten",
        help="Preserve group structure from SVG",
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Check if input exists
    if not input_path.exists():
        print(f"Error: Input path '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    # Create configuration
    config = Config(
        scale=args.scale,
        flatten_groups=args.flatten,
        convert_text=not args.no_text,
        convert_shapes=not args.no_shapes,
    )

    # Batch mode: input is a directory
    if input_path.is_dir():
        # Output must be a directory in batch mode
        if output_path.exists() and not output_path.is_dir():
            print(f"Error: Output '{args.output}' must be a directory for batch conversion.", file=sys.stderr)
            sys.exit(1)
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        success, failures = convert_folder(input_path, output_path, config, recursive=args.recursive)
        
        print(f"\nBatch conversion complete: {success} succeeded, {failures} failed")
        
        if failures > 0:
            sys.exit(1)
    
    # Single file mode
    else:
        if args.recursive:
            print("Warning: --recursive flag is ignored for single file conversion.", file=sys.stderr)
        
        if not input_path.suffix.lower() == ".svg":
            print(f"Warning: Input file '{args.input}' does not have .svg extension.", file=sys.stderr)

        if not output_path.suffix.lower() == ".pptx":
            print(f"Warning: Output file '{args.output}' does not have .pptx extension.", file=sys.stderr)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if convert_single_file(input_path, output_path, config):
            print(f"Successfully converted '{args.input}' to '{args.output}'")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
