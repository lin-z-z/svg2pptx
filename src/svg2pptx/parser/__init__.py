"""SVG parser module."""

from svg2pptx.parser.svg_parser import SVGParser
from svg2pptx.parser.shapes import parse_shape
from svg2pptx.parser.paths import parse_path
from svg2pptx.parser.transforms import parse_transform, Transform
from svg2pptx.parser.styles import parse_style, Style

__all__ = [
    "SVGParser",
    "parse_shape",
    "parse_path",
    "parse_transform",
    "Transform",
    "parse_style",
    "Style",
]
