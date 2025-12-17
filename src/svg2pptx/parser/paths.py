"""SVG path element parsing using svgpathtools."""

from dataclasses import dataclass, field
from typing import Optional

from svg2pptx.parser.styles import Style, parse_style
from svg2pptx.parser.transforms import Transform, parse_transform
from svg2pptx.geometry.curves import bezier_to_lines, svg_arc_to_lines


@dataclass
class PathShape:
    """
    Parsed SVG path data.

    A path consists of one or more subpaths (contours).
    Each subpath is a list of points and a closed flag.
    """

    shape_type: str = "path"
    style: Style = field(default_factory=Style)
    transform: Transform = field(default_factory=Transform.identity)
    element_id: Optional[str] = None
    subpaths: list[tuple[list[tuple[float, float]], bool]] = field(
        default_factory=list
    )


def parse_path(
    element,
    parent_style: Optional[Style] = None,
    parent_transform: Optional[Transform] = None,
    curve_tolerance: float = 1.0,
) -> Optional[PathShape]:
    """
    Parse an SVG path element.

    Uses svgpathtools to parse the d attribute, then converts Bezier curves
    to line segments using the specified tolerance.

    Args:
        element: ElementTree element for a <path>.
        parent_style: Parent element's style for inheritance.
        parent_transform: Parent element's transform.
        curve_tolerance: Tolerance for Bezier curve approximation.

    Returns:
        PathShape object or None if parsing fails.
    """
    try:
        from svgpathtools import parse_path as svgpathtools_parse
        from svgpathtools import Line, CubicBezier, QuadraticBezier, Arc
    except ImportError:
        # Fallback if svgpathtools not available
        return _parse_path_basic(
            element, parent_style, parent_transform, curve_tolerance
        )

    # Parse common attributes
    style = parse_style(element, parent_style)
    local_transform = parse_transform(element.get("transform", ""))
    element_id = element.get("id")

    if parent_transform:
        transform = parent_transform.compose(local_transform)
    else:
        transform = local_transform

    # Get the d attribute
    d_attr = element.get("d", "")
    if not d_attr:
        return None

    try:
        path = svgpathtools_parse(d_attr)
    except Exception:
        return None

    # Convert svgpathtools path to point lists
    subpaths = []
    current_points: list[tuple[float, float]] = []
    current_start: Optional[tuple[float, float]] = None

    for segment in path:
        start = (segment.start.real, segment.start.imag)
        end = (segment.end.real, segment.end.imag)

        # Check if this is a new subpath (move command)
        if not current_points or start != (
            current_points[-1] if current_points else None
        ):
            if current_points:
                # Save previous subpath
                is_closed = (
                    current_start is not None
                    and len(current_points) > 1
                    and _points_close(current_points[-1], current_start)
                )
                subpaths.append((current_points, is_closed))
            current_points = [start]
            current_start = start

        if isinstance(segment, Line):
            current_points.append(end)

        elif isinstance(segment, CubicBezier):
            ctrl1 = (segment.control1.real, segment.control1.imag)
            ctrl2 = (segment.control2.real, segment.control2.imag)
            line_points = bezier_to_lines(
                start, ctrl1, ctrl2, end, tolerance=curve_tolerance
            )
            current_points.extend(line_points)

        elif isinstance(segment, QuadraticBezier):
            ctrl = (segment.control.real, segment.control.imag)
            line_points = bezier_to_lines(
                start, ctrl, end, tolerance=curve_tolerance
            )
            current_points.extend(line_points)

        elif isinstance(segment, Arc):
            # Convert arc to line segments
            arc_points = svg_arc_to_lines(
                x1=start[0],
                y1=start[1],
                rx=segment.radius.real,
                ry=segment.radius.imag,
                x_axis_rotation=segment.rotation,
                large_arc_flag=segment.large_arc,
                sweep_flag=segment.sweep,
                x2=end[0],
                y2=end[1],
                tolerance=curve_tolerance,
            )
            current_points.extend(arc_points)

    # Add final subpath
    if current_points:
        is_closed = (
            current_start is not None
            and len(current_points) > 1
            and _points_close(current_points[-1], current_start)
        )
        subpaths.append((current_points, is_closed))

    if not subpaths:
        return None

    return PathShape(
        shape_type="path",
        style=style,
        transform=transform,
        element_id=element_id,
        subpaths=subpaths,
    )


def _points_close(
    p1: tuple[float, float], p2: tuple[float, float], epsilon: float = 0.01
) -> bool:
    """Check if two points are close enough to be considered equal."""
    return abs(p1[0] - p2[0]) < epsilon and abs(p1[1] - p2[1]) < epsilon


def _parse_path_basic(
    element,
    parent_style: Optional[Style] = None,
    parent_transform: Optional[Transform] = None,
    curve_tolerance: float = 1.0,
) -> Optional[PathShape]:
    """
    Basic path parsing fallback without svgpathtools.

    Only handles simple commands: M, L, H, V, Z.
    """
    import re

    style = parse_style(element, parent_style)
    local_transform = parse_transform(element.get("transform", ""))
    element_id = element.get("id")

    if parent_transform:
        transform = parent_transform.compose(local_transform)
    else:
        transform = local_transform

    d_attr = element.get("d", "")
    if not d_attr:
        return None

    # Tokenize the d attribute
    tokens = re.findall(r"([MmLlHhVvZzCcSsQqTtAa])|(-?[\d.]+)", d_attr)

    subpaths = []
    current_points: list[tuple[float, float]] = []
    current_x, current_y = 0.0, 0.0
    subpath_start = (0.0, 0.0)
    command = ""

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token[0]:  # It's a command
            command = token[0]
            i += 1
        elif token[1]:  # It's a number
            if command.upper() == "M":
                x = float(token[1])
                i += 1
                y = float(tokens[i][1]) if i < len(tokens) else 0
                i += 1
                if command == "m":
                    x += current_x
                    y += current_y
                if current_points:
                    is_closed = _points_close(
                        current_points[-1], subpath_start
                    )
                    subpaths.append((current_points, is_closed))
                current_points = [(x, y)]
                current_x, current_y = x, y
                subpath_start = (x, y)
                command = "L" if command == "M" else "l"

            elif command.upper() == "L":
                x = float(token[1])
                i += 1
                y = float(tokens[i][1]) if i < len(tokens) else 0
                i += 1
                if command == "l":
                    x += current_x
                    y += current_y
                current_points.append((x, y))
                current_x, current_y = x, y

            elif command.upper() == "H":
                x = float(token[1])
                i += 1
                if command == "h":
                    x += current_x
                current_points.append((x, current_y))
                current_x = x

            elif command.upper() == "V":
                y = float(token[1])
                i += 1
                if command == "v":
                    y += current_y
                current_points.append((current_x, y))
                current_y = y

            elif command.upper() == "Z":
                current_points.append(subpath_start)
                subpaths.append((current_points, True))
                current_points = []
                current_x, current_y = subpath_start
                i += 1

            else:
                # Skip unsupported commands
                i += 1
        else:
            i += 1

    # Add final subpath
    if current_points:
        is_closed = _points_close(current_points[-1], subpath_start)
        subpaths.append((current_points, is_closed))

    if not subpaths:
        return None

    return PathShape(
        shape_type="path",
        style=style,
        transform=transform,
        element_id=element_id,
        subpaths=subpaths,
    )
