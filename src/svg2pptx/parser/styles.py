"""SVG style attribute parsing."""

import re
from dataclasses import dataclass, field
from typing import Optional


# Named CSS colors to RGB hex
CSS_COLORS = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "cyan": "#00ffff",
    "magenta": "#ff00ff",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#c0c0c0",
    "maroon": "#800000",
    "olive": "#808000",
    "lime": "#00ff00",
    "aqua": "#00ffff",
    "teal": "#008080",
    "navy": "#000080",
    "fuchsia": "#ff00ff",
    "purple": "#800080",
    "orange": "#ffa500",
    "pink": "#ffc0cb",
    "brown": "#a52a2a",
    "coral": "#ff7f50",
    "crimson": "#dc143c",
    "darkblue": "#00008b",
    "darkgray": "#a9a9a9",
    "darkgreen": "#006400",
    "darkred": "#8b0000",
    "gold": "#ffd700",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lightblue": "#add8e6",
    "lightgray": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightyellow": "#ffffe0",
    "skyblue": "#87ceeb",
    "steelblue": "#4682b4",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "transparent": "none",
}

# Pattern for rgb() and rgba() colors
RGB_PATTERN = re.compile(
    r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", re.IGNORECASE
)
RGBA_PATTERN = re.compile(
    r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)",
    re.IGNORECASE,
)


@dataclass
class Style:
    """
    Parsed SVG style attributes.

    Attributes:
        fill: Fill color as hex string or "none".
        fill_opacity: Fill opacity (0.0 to 1.0).
        stroke: Stroke color as hex string or "none".
        stroke_width: Stroke width in pixels.
        stroke_opacity: Stroke opacity (0.0 to 1.0).
        opacity: Overall opacity (0.0 to 1.0).
        font_family: Font family name.
        font_size: Font size in pixels.
        font_weight: Font weight (normal, bold, or numeric).
        text_anchor: Text anchor (start, middle, end).
    """

    fill: str = "none"
    fill_opacity: float = 1.0
    stroke: str = "none"
    stroke_width: float = 1.0
    stroke_opacity: float = 1.0
    opacity: float = 1.0
    font_family: str = "Arial"
    font_size: float = 12.0
    font_weight: str = "normal"
    text_anchor: str = "start"

    def with_parent(self, parent: "Style") -> "Style":
        """
        Create a new style inheriting from a parent style.

        Child values override parent values if explicitly set.
        """
        return Style(
            fill=self.fill if self.fill != "inherit" else parent.fill,
            fill_opacity=self.fill_opacity,
            stroke=self.stroke if self.stroke != "inherit" else parent.stroke,
            stroke_width=self.stroke_width,
            stroke_opacity=self.stroke_opacity,
            opacity=self.opacity * parent.opacity,
            font_family=(
                self.font_family
                if self.font_family != "inherit"
                else parent.font_family
            ),
            font_size=(
                self.font_size
                if self.font_size > 0
                else parent.font_size
            ),
            font_weight=(
                self.font_weight
                if self.font_weight != "inherit"
                else parent.font_weight
            ),
            text_anchor=(
                self.text_anchor
                if self.text_anchor != "inherit"
                else parent.text_anchor
            ),
        )

    @property
    def effective_fill_opacity(self) -> float:
        """Combined fill and overall opacity."""
        return self.fill_opacity * self.opacity

    @property
    def effective_stroke_opacity(self) -> float:
        """Combined stroke and overall opacity."""
        return self.stroke_opacity * self.opacity


def parse_color(color_str: str) -> str:
    """
    Parse an SVG/CSS color value.

    Args:
        color_str: Color string (hex, rgb(), named color, or "none").

    Returns:
        Normalized hex color string (e.g., "#ff0000") or "none".
    """
    if not color_str:
        return "none"

    color_str = color_str.strip().lower()

    # Handle special values
    if color_str in ("none", "transparent", ""):
        return "none"
    if color_str == "currentcolor":
        return "#000000"  # Default to black

    # Named colors
    if color_str in CSS_COLORS:
        return CSS_COLORS[color_str]

    # Hex colors
    if color_str.startswith("#"):
        if len(color_str) == 4:
            # Short hex (#rgb -> #rrggbb)
            return "#" + "".join(c * 2 for c in color_str[1:])
        elif len(color_str) == 7:
            return color_str
        elif len(color_str) == 9:
            # #rrggbbaa - strip alpha
            return color_str[:7]

    # rgb() format
    rgb_match = RGB_PATTERN.match(color_str)
    if rgb_match:
        r, g, b = [int(x) for x in rgb_match.groups()]
        return f"#{r:02x}{g:02x}{b:02x}"

    # rgba() format
    rgba_match = RGBA_PATTERN.match(color_str)
    if rgba_match:
        r, g, b = [int(x) for x in rgba_match.groups()[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"

    # Unknown format, return as-is
    return color_str


def parse_style_attribute(style_str: str) -> dict[str, str]:
    """
    Parse CSS-style attribute string.

    Args:
        style_str: Style attribute value (e.g., "fill: red; stroke-width: 2").

    Returns:
        Dictionary of property name to value.
    """
    if not style_str:
        return {}

    result = {}
    for declaration in style_str.split(";"):
        declaration = declaration.strip()
        if ":" in declaration:
            prop, value = declaration.split(":", 1)
            result[prop.strip().lower()] = value.strip()

    return result


def parse_style(
    element,
    parent_style: Optional[Style] = None,
    default_fill: str = "none",
    default_stroke: str = "none",
) -> Style:
    """
    Parse style from an SVG element.

    Combines inline style attribute and direct presentation attributes.

    Args:
        element: ElementTree element.
        parent_style: Parent element's style for inheritance.
        default_fill: Default fill color.
        default_stroke: Default stroke color.

    Returns:
        Parsed Style object.
    """
    # Start with defaults or inherit from parent
    if parent_style:
        style = Style(
            fill=parent_style.fill,
            fill_opacity=parent_style.fill_opacity,
            stroke=parent_style.stroke,
            stroke_width=parent_style.stroke_width,
            stroke_opacity=parent_style.stroke_opacity,
            opacity=parent_style.opacity,
            font_family=parent_style.font_family,
            font_size=parent_style.font_size,
            font_weight=parent_style.font_weight,
            text_anchor=parent_style.text_anchor,
        )
    else:
        style = Style(fill=default_fill, stroke=default_stroke)

    # Parse inline style attribute
    style_attr = element.get("style", "")
    style_dict = parse_style_attribute(style_attr)

    # Helper to get attribute from style or direct attribute
    def get_attr(name: str, default: Optional[str] = None) -> Optional[str]:
        # Style attribute takes precedence
        if name in style_dict:
            return style_dict[name]
        # Then direct attribute
        val = element.get(name)
        if val is not None:
            return val
        return default

    # Parse fill
    fill_val = get_attr("fill")
    if fill_val is not None:
        style.fill = parse_color(fill_val)

    # Parse fill-opacity
    fill_opacity_val = get_attr("fill-opacity")
    if fill_opacity_val is not None:
        try:
            style.fill_opacity = float(fill_opacity_val)
        except ValueError:
            pass

    # Parse stroke
    stroke_val = get_attr("stroke")
    if stroke_val is not None:
        style.stroke = parse_color(stroke_val)

    # Parse stroke-width
    stroke_width_val = get_attr("stroke-width")
    if stroke_width_val is not None:
        try:
            # Remove unit suffix if present
            width_str = re.sub(r"[a-z]+$", "", stroke_width_val.strip(), flags=re.I)
            style.stroke_width = float(width_str)
        except ValueError:
            pass

    # Parse stroke-opacity
    stroke_opacity_val = get_attr("stroke-opacity")
    if stroke_opacity_val is not None:
        try:
            style.stroke_opacity = float(stroke_opacity_val)
        except ValueError:
            pass

    # Parse opacity
    opacity_val = get_attr("opacity")
    if opacity_val is not None:
        try:
            style.opacity = float(opacity_val)
        except ValueError:
            pass

    # Parse font properties
    font_family_val = get_attr("font-family")
    if font_family_val is not None:
        # Remove quotes
        style.font_family = font_family_val.strip("'\"")

    font_size_val = get_attr("font-size")
    if font_size_val is not None:
        try:
            # Simple parsing, assumes px
            size_str = re.sub(r"[a-z]+$", "", font_size_val.strip(), flags=re.I)
            style.font_size = float(size_str)
        except ValueError:
            pass

    font_weight_val = get_attr("font-weight")
    if font_weight_val is not None:
        style.font_weight = font_weight_val

    text_anchor_val = get_attr("text-anchor")
    if text_anchor_val is not None:
        style.text_anchor = text_anchor_val

    return style
