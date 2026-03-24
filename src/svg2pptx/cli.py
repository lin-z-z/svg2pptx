"""Command-line interface for SVG to PowerPoint conversion."""

import argparse
import json
import sys
from pathlib import Path

from svg2pptx import Config, __version__, convert_svg_inputs


def _build_config(args: argparse.Namespace) -> Config:
    preserve_groups = not args.flatten
    return Config(
        scale=args.scale,
        curve_tolerance=args.curve_tolerance,
        preserve_groups=preserve_groups,
        flatten_groups=args.flatten,
        convert_text=not args.no_text,
        convert_shapes=not args.no_shapes,
    )


def _write_json_report(report_path: Path, report: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_error_report(args: argparse.Namespace, message: str) -> dict:
    return {
        "schema_version": "1.0",
        "status": "error",
        "input": {
            "path": args.input,
            "kind": "unknown",
            "recursive": args.recursive,
        },
        "output": {
            "path": args.output,
            "kind": "unknown",
        },
        "config": {
            "scale": args.scale,
            "curve_tolerance": args.curve_tolerance,
            "flatten_groups": args.flatten,
            "convert_text": not args.no_text,
            "convert_shapes": not args.no_shapes,
        },
        "totals": {
            "input_count": 0,
            "success_count": 0,
            "failure_count": 1,
        },
        "results": [],
        "error": message,
    }


def _print_human_summary(report: dict) -> None:
    if report["input"]["kind"] == "directory":
        print(
            "Batch conversion complete: "
            f"{report['totals']['success_count']} succeeded, "
            f"{report['totals']['failure_count']} failed"
        )
        for result in report["results"]:
            output_name = Path(result["output_path"]).name
            input_name = Path(result["input_path"]).name
            if result["status"] == "success":
                print(f"  ✓ {input_name} → {output_name}")
            else:
                print(f"  ✗ {input_name}: {result['error']}")
    else:
        result = report["results"][0] if report["results"] else None
        if result and result["status"] == "success":
            print(
                f"Successfully converted '{result['input_path']}' "
                f"to '{result['output_path']}'"
            )
        else:
            error = result["error"] if result else report.get("error", "unknown error")
            print(error, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
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
  svg2pptx ./icons/ ./converted/ --recursive --report-json ./converted/report.json
  svg2pptx ./assets/ ./assets/ --json
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
        "--curve-tolerance",
        type=float,
        default=1.0,
        help="Curve approximation tolerance (default: 1.0)",
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the structured conversion report as JSON.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Write the structured conversion report to a JSON file.",
    )

    args = parser.parse_args(argv)

    try:
        report = convert_svg_inputs(
            args.input,
            args.output,
            config=_build_config(args),
            recursive=args.recursive,
        )
    except Exception as exc:
        report = _build_error_report(args, str(exc))

    if args.report_json is not None:
        _write_json_report(args.report_json, report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human_summary(report)

    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
