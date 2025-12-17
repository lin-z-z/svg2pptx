"""
SVG to PowerPoint Shape Converter

Convert SVG files to native, editable PowerPoint shapes.
"""

from svg2pptx.converter import SVGConverter
from svg2pptx.config import Config

__version__ = "0.1.0"
__all__ = ["svg_to_pptx", "SVGConverter", "Config"]


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
