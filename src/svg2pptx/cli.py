"""Command-line interface for SVG to PowerPoint conversion."""

import argparse
import sys
from pathlib import Path

from svg2pptx import svg_to_pptx, Config, __version__


def main():
    """Main entry point for the svg2pptx CLI."""
    parser = argparse.ArgumentParser(
        prog="svg2pptx",
        description="Convert SVG files to native, editable PowerPoint shapes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  svg2pptx input.svg output.pptx
  svg2pptx diagram.svg presentation.pptx --no-text
  svg2pptx icon.svg slides.pptx --no-shapes
  svg2pptx logo.svg doc.pptx --no-text --no-shapes
        """,
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to the input SVG file",
    )

    parser.add_argument(
        "output",
        type=str,
        help="Path for the output PowerPoint file",
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

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    if not input_path.suffix.lower() == ".svg":
        print(f"Warning: Input file '{args.input}' does not have .svg extension.", file=sys.stderr)

    # Validate output path
    output_path = Path(args.output)
    if not output_path.suffix.lower() == ".pptx":
        print(f"Warning: Output file '{args.output}' does not have .pptx extension.", file=sys.stderr)

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create configuration
    config = Config(
        scale=args.scale,
        flatten_groups=args.flatten,
        convert_text=not args.no_text,
        convert_shapes=not args.no_shapes,
    )

    try:
        svg_to_pptx(str(input_path), str(output_path), config=config)
        print(f"Successfully converted '{args.input}' to '{args.output}'")
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
