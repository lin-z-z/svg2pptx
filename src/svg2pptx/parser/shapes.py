"""SVG basic shape element parsing."""

from dataclasses import dataclass, field
from typing import Optional
from xml.etree.ElementTree import Element

from svg2pptx.geometry.units import parse_length
from svg2pptx.parser.styles import Style, parse_style
from svg2pptx.parser.transforms import Transform, parse_transform


@dataclass
class ParsedShape:
    """
    Base class for parsed SVG shape data.

    Attributes:
        shape_type: Type of shape (rect, circle, ellipse, line, polygon, polyline).
        style: Parsed style information.
        transform: Local transform for this shape.
        element_id: Optional ID attribute from SVG.
    """

    shape_type: str
    style: Style
    transform: Transform = field(default_factory=Transform.identity)
    element_id: Optional[str] = None


@dataclass
class RectShape(ParsedShape):
    """Rectangle shape data."""

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rx: float = 0.0  # Corner radius X
    ry: float = 0.0  # Corner radius Y

    def __post_init__(self):
        self.shape_type = "rect"


@dataclass
class CircleShape(ParsedShape):
    """Circle shape data."""

    cx: float = 0.0
    cy: float = 0.0
    r: float = 0.0

    def __post_init__(self):
        self.shape_type = "circle"


@dataclass
class EllipseShape(ParsedShape):
    """Ellipse shape data."""

    cx: float = 0.0
    cy: float = 0.0
    rx: float = 0.0
    ry: float = 0.0

    def __post_init__(self):
        self.shape_type = "ellipse"


@dataclass
class LineShape(ParsedShape):
    """Line shape data."""

    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0

    def __post_init__(self):
        self.shape_type = "line"


@dataclass
class PolygonShape(ParsedShape):
    """Polygon shape data (closed)."""

    points: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self):
        self.shape_type = "polygon"


@dataclass
class PolylineShape(ParsedShape):
    """Polyline shape data (open)."""

    points: list[tuple[float, float]] = field(default_factory=list)

    def __post_init__(self):
        self.shape_type = "polyline"


def parse_points(points_str: str) -> list[tuple[float, float]]:
    """
    Parse SVG points attribute (used by polygon and polyline).

    Handles formats like:
        "100,200 300,400"
        "100 200 300 400"
        "100,200,300,400"

    Args:
        points_str: Points attribute value.

    Returns:
        List of (x, y) tuples.
    """
    if not points_str:
        return []

    import re
    # Split by whitespace and/or commas
    values = re.split(r"[\s,]+", points_str.strip())
    values = [v for v in values if v]  # Remove empty strings

    points = []
    for i in range(0, len(values) - 1, 2):
        try:
            x = float(values[i])
            y = float(values[i + 1])
            points.append((x, y))
        except (ValueError, IndexError):
            continue

    return points


def parse_shape(
    element: Element,
    parent_style: Optional[Style] = None,
    parent_transform: Optional[Transform] = None,
) -> Optional[ParsedShape]:
    """
    Parse an SVG shape element into a ParsedShape object.

    Supported elements: rect, circle, ellipse, line, polygon, polyline.

    Args:
        element: ElementTree element.
        parent_style: Parent element's style for inheritance.
        parent_transform: Parent element's transform.

    Returns:
        ParsedShape object or None if element is not a recognized shape.
    """
    # Get tag name without namespace
    tag = element.tag
    if "}" in tag:
        tag = tag.split("}")[-1]
    tag = tag.lower()

    # Parse common attributes
    style = parse_style(element, parent_style)
    local_transform = parse_transform(element.get("transform", ""))
    element_id = element.get("id")

    # Combine with parent transform
    if parent_transform:
        transform = parent_transform.compose(local_transform)
    else:
        transform = local_transform

    # Helper function to get float attribute
    def get_float(name: str, default: float = 0.0) -> float:
        val = element.get(name)
        if val is None:
            return default
        try:
            return parse_length(val)
        except ValueError:
            return default

    if tag == "rect":
        return RectShape(
            shape_type="rect",
            style=style,
            transform=transform,
            element_id=element_id,
            x=get_float("x"),
            y=get_float("y"),
            width=get_float("width"),
            height=get_float("height"),
            rx=get_float("rx"),
            ry=get_float("ry", get_float("rx")),  # ry defaults to rx
        )

    elif tag == "circle":
        return CircleShape(
            shape_type="circle",
            style=style,
            transform=transform,
            element_id=element_id,
            cx=get_float("cx"),
            cy=get_float("cy"),
            r=get_float("r"),
        )

    elif tag == "ellipse":
        return EllipseShape(
            shape_type="ellipse",
            style=style,
            transform=transform,
            element_id=element_id,
            cx=get_float("cx"),
            cy=get_float("cy"),
            rx=get_float("rx"),
            ry=get_float("ry"),
        )

    elif tag == "line":
        return LineShape(
            shape_type="line",
            style=style,
            transform=transform,
            element_id=element_id,
            x1=get_float("x1"),
            y1=get_float("y1"),
            x2=get_float("x2"),
            y2=get_float("y2"),
        )

    elif tag == "polygon":
        points = parse_points(element.get("points", ""))
        return PolygonShape(
            shape_type="polygon",
            style=style,
            transform=transform,
            element_id=element_id,
            points=points,
        )

    elif tag == "polyline":
        points = parse_points(element.get("points", ""))
        return PolylineShape(
            shape_type="polyline",
            style=style,
            transform=transform,
            element_id=element_id,
            points=points,
        )

    return None
