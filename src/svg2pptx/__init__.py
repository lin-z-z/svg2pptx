"""
SVG to PowerPoint Shape Converter

Convert SVG files to native, editable PowerPoint shapes.
"""

from pathlib import Path

from svg2pptx.converter import SVGConverter
from svg2pptx.config import Config

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("svg2pptx")
    except PackageNotFoundError:
        __version__ = "0.0.0.dev0"  # Fallback for development
except ImportError:
    __version__ = "0.0.0.dev0"  # Python < 3.8 fallback

__all__ = [
    "convert_svg_inputs",
    "svg_to_pptx",
    "SVGConverter",
    "Config",
    "__version__",
]


def svg_to_pptx(
    svg_path: str,
    pptx_path: str,
    config: Config = None,
) -> None:
    """
    Convert an SVG file to a PowerPoint presentation.

    Args:
        svg_path: Path to the input SVG file.
        pptx_path: Path for the output PowerPoint file.
        config: Optional configuration settings.

    Example:
        >>> from svg2pptx import svg_to_pptx
        >>> svg_to_pptx("icon.svg", "output.pptx")
    """
    converter = SVGConverter(config=config)
    converter.convert_file(svg_path, pptx_path)


def _config_snapshot(config: Config) -> dict:
    return {
        "scale": config.scale,
        "curve_tolerance": config.curve_tolerance,
        "preserve_groups": config.preserve_groups,
        "flatten_groups": config.flatten_groups,
        "convert_text": config.convert_text,
        "convert_shapes": config.convert_shapes,
        "slide_width": config.slide_width,
        "slide_height": config.slide_height,
    }


def _build_result_item(
    input_path: Path,
    output_path: Path,
    status: str,
    converter: SVGConverter,
    error: str = "",
) -> dict:
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "status": status,
        "error": error,
        "gradient_stats": dict(converter.config.gradient_stats),
        "render_metrics": dict(converter.config.render_metrics),
        "render_warnings": list(converter.config.render_warnings),
        "unsupported_styles": list(converter.config.unsupported_styles),
    }


def convert_svg_inputs(
    input_path: str | Path,
    output_path: str | Path,
    config: Config | None = None,
    recursive: bool = False,
) -> dict:
    """
    Convert one SVG file or a directory of SVG files and return a structured report.

    Args:
        input_path: SVG file path or directory containing SVG files.
        output_path: PPTX output path for single-file mode, or output directory.
        config: Optional conversion config shared by the whole run.
        recursive: Whether to recurse into subdirectories for directory input.

    Returns:
        Structured conversion report with totals and per-file diagnostics.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input path '{input_path}' not found.")

    active_config = config or Config()
    converter = SVGConverter(config=active_config)

    if input_path.is_dir():
        svg_files = sorted(
            input_path.rglob("*.svg") if recursive else input_path.glob("*.svg")
        )
        if not svg_files:
            raise ValueError(f"No SVG files found in '{input_path}'.")
        if output_path.exists() and not output_path.is_dir():
            raise ValueError(
                f"Output '{output_path}' must be a directory for directory input."
            )
        output_path.mkdir(parents=True, exist_ok=True)
        input_kind = "directory"
        output_kind = "directory"
    else:
        svg_files = [input_path]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_kind = "file"
        output_kind = "file"

    results: list[dict] = []
    for svg_file in svg_files:
        if input_kind == "directory":
            if recursive:
                relative_path = svg_file.relative_to(input_path)
                pptx_path = output_path / relative_path.with_suffix(".pptx")
            else:
                pptx_path = output_path / svg_file.with_suffix(".pptx").name
            pptx_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            pptx_path = output_path

        try:
            converter.convert_file(svg_file, pptx_path)
        except Exception as exc:
            results.append(
                _build_result_item(
                    svg_file,
                    pptx_path,
                    status="error",
                    converter=converter,
                    error=str(exc),
                )
            )
        else:
            results.append(
                _build_result_item(
                    svg_file,
                    pptx_path,
                    status="success",
                    converter=converter,
                )
            )

    failure_count = sum(1 for item in results if item["status"] != "success")
    success_count = len(results) - failure_count
    if failure_count == 0:
        status = "success"
    elif success_count == 0:
        status = "error"
    else:
        status = "partial_failure"

    return {
        "schema_version": "1.0",
        "status": status,
        "input": {
            "path": str(input_path),
            "kind": input_kind,
            "recursive": recursive,
        },
        "output": {
            "path": str(output_path),
            "kind": output_kind,
        },
        "config": _config_snapshot(active_config),
        "totals": {
            "input_count": len(results),
            "success_count": success_count,
            "failure_count": failure_count,
        },
        "results": results,
    }
