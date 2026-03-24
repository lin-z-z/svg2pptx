"""Affine transformation matrix operations for SVG transforms."""

import re
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class Transform:
    """
    2D affine transformation matrix.

    Represents the transformation:
        | a  c  e |
        | b  d  f |
        | 0  0  1 |

    Where:
        new_x = a * x + c * y + e
        new_y = b * x + d * y + f
    """

    a: float = 1.0  # scale x
    b: float = 0.0  # skew y
    c: float = 0.0  # skew x
    d: float = 1.0  # scale y
    e: float = 0.0  # translate x
    f: float = 0.0  # translate y

    @classmethod
    def identity(cls) -> "Transform":
        """Create an identity transformation."""
        return cls()

    @classmethod
    def translate(cls, tx: float, ty: float = 0) -> "Transform":
        """Create a translation transformation."""
        return cls(e=tx, f=ty)

    @classmethod
    def scale(cls, sx: float, sy: Optional[float] = None) -> "Transform":
        """Create a scale transformation."""
        if sy is None:
            sy = sx
        return cls(a=sx, d=sy)

    @classmethod
    def rotate(
        cls, angle_deg: float, cx: float = 0, cy: float = 0
    ) -> "Transform":
        """
        Create a rotation transformation.

        Args:
            angle_deg: Rotation angle in degrees.
            cx: Center of rotation X coordinate.
            cy: Center of rotation Y coordinate.
        """
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        if cx == 0 and cy == 0:
            return cls(a=cos_a, b=sin_a, c=-sin_a, d=cos_a)

        # rotate(angle, cx, cy) = translate(cx, cy) rotate(angle) translate(-cx, -cy)
        return cls(
            a=cos_a,
            b=sin_a,
            c=-sin_a,
            d=cos_a,
            e=cx - cos_a * cx + sin_a * cy,
            f=cy - sin_a * cx - cos_a * cy,
        )

    @classmethod
    def skew_x(cls, angle_deg: float) -> "Transform":
        """Create a skew X transformation."""
        return cls(c=math.tan(math.radians(angle_deg)))

    @classmethod
    def skew_y(cls, angle_deg: float) -> "Transform":
        """Create a skew Y transformation."""
        return cls(b=math.tan(math.radians(angle_deg)))

    @classmethod
    def from_matrix(
        cls, a: float, b: float, c: float, d: float, e: float, f: float
    ) -> "Transform":
        """Create transformation from matrix values."""
        return cls(a=a, b=b, c=c, d=d, e=e, f=f)

    def apply(self, x: float, y: float) -> tuple[float, float]:
        """Apply transformation to a point."""
        new_x = self.a * x + self.c * y + self.e
        new_y = self.b * x + self.d * y + self.f
        return (new_x, new_y)

    def apply_to_points(
        self, points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """Apply transformation to a list of points."""
        return [self.apply(x, y) for x, y in points]

    def compose(self, other: "Transform") -> "Transform":
        """
        Compose this transformation with another.

        Returns a new transformation equivalent to applying 'other' first,
        then 'self'.
        """
        return Transform(
            a=self.a * other.a + self.c * other.b,
            b=self.b * other.a + self.d * other.b,
            c=self.a * other.c + self.c * other.d,
            d=self.b * other.c + self.d * other.d,
            e=self.a * other.e + self.c * other.f + self.e,
            f=self.b * other.e + self.d * other.f + self.f,
        )

    def __repr__(self) -> str:
        return f"Transform(a={self.a}, b={self.b}, c={self.c}, d={self.d}, e={self.e}, f={self.f})"


def compose_transforms(transforms: list[Transform]) -> Transform:
    """
    Compose a list of transformations in order.

    Args:
        transforms: List of Transform objects to compose.

    Returns:
        Single Transform representing the composition.
    """
    result = Transform.identity()
    for t in transforms:
        # SVG transform lists are applied from left to right as written.
        result = t.compose(result)
    return result


def points_to_bbox(
    points: list[tuple[float, float]]
) -> tuple[float, float, float, float]:
    """
    Convert a point collection to an axis-aligned bounding box.

    Args:
        points: List of (x, y) tuples.

    Returns:
        Bounding box as (left, top, width, height).
    """
    if not points:
        raise ValueError("points must not be empty")

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left = min(xs)
    top = min(ys)
    return (left, top, max(xs) - left, max(ys) - top)


def transform_rect_to_bbox(
    x: float,
    y: float,
    width: float,
    height: float,
    transform: Transform,
) -> tuple[float, float, float, float]:
    """
    Project a rectangle through an affine transform and return its bbox.

    Args:
        x: Rectangle left coordinate.
        y: Rectangle top coordinate.
        width: Rectangle width.
        height: Rectangle height.
        transform: Affine transform to apply.

    Returns:
        Bounding box as (left, top, width, height).
    """
    corners = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    ]
    return points_to_bbox(transform.apply_to_points(corners))


def transform_ellipse_to_bbox(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    transform: Transform,
) -> tuple[float, float, float, float]:
    """
    Project an ellipse through an affine transform and return its bbox.

    This keeps the geometry work inside the geometry layer so grouped and
    flattened writers can consume the same global bbox contract.

    Args:
        cx: Ellipse center x.
        cy: Ellipse center y.
        rx: Ellipse x radius.
        ry: Ellipse y radius.
        transform: Affine transform to apply.

    Returns:
        Bounding box as (left, top, width, height).
    """
    center_x, center_y = transform.apply(cx, cy)
    axis_x_end = transform.apply(cx + rx, cy)
    axis_y_end = transform.apply(cx, cy + ry)

    axis_x = (axis_x_end[0] - center_x, axis_x_end[1] - center_y)
    axis_y = (axis_y_end[0] - center_x, axis_y_end[1] - center_y)

    half_width = math.sqrt(axis_x[0] ** 2 + axis_y[0] ** 2)
    half_height = math.sqrt(axis_x[1] ** 2 + axis_y[1] ** 2)
    return (
        center_x - half_width,
        center_y - half_height,
        half_width * 2,
        half_height * 2,
    )


# Regex patterns for parsing transform functions
TRANSFORM_PATTERN = re.compile(
    r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]+)\)",
    re.IGNORECASE,
)


def parse_transform(transform_str: str) -> Transform:
    """
    Parse an SVG transform attribute string.

    Args:
        transform_str: SVG transform attribute value
            (e.g., "translate(10, 20) rotate(45)").

    Returns:
        Combined Transform object.
    """
    if not transform_str:
        return Transform.identity()

    transforms = []

    for match in TRANSFORM_PATTERN.finditer(transform_str):
        func_name = match.group(1).lower()
        args_str = match.group(2)
        args = [float(x) for x in re.split(r"[\s,]+", args_str.strip()) if x]

        if func_name == "matrix" and len(args) == 6:
            transforms.append(Transform.from_matrix(*args))
        elif func_name == "translate":
            tx = args[0] if len(args) >= 1 else 0
            ty = args[1] if len(args) >= 2 else 0
            transforms.append(Transform.translate(tx, ty))
        elif func_name == "scale":
            sx = args[0] if len(args) >= 1 else 1
            sy = args[1] if len(args) >= 2 else sx
            transforms.append(Transform.scale(sx, sy))
        elif func_name == "rotate":
            angle = args[0] if len(args) >= 1 else 0
            cx = args[1] if len(args) >= 2 else 0
            cy = args[2] if len(args) >= 3 else 0
            transforms.append(Transform.rotate(angle, cx, cy))
        elif func_name == "skewx":
            transforms.append(Transform.skew_x(args[0] if args else 0))
        elif func_name == "skewy":
            transforms.append(Transform.skew_y(args[0] if args else 0))

    return compose_transforms(transforms)
