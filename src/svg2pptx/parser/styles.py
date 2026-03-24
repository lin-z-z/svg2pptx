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

# Pattern for gradient references like url(#gradientId)
URL_REF_PATTERN = re.compile(r"url\s*\(\s*#([^)]+)\s*\)", re.IGNORECASE)


@dataclass
class GradientStop:
    """One gradient stop resolved from SVG defs."""

    offset: float
    color: str
    opacity: float = 1.0


@dataclass
class GradientSpec:
    """Resolved SVG gradient definition used by the writer layer."""

    gradient_id: str
    kind: str
    stops: list[GradientStop] = field(default_factory=list)
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 1.0
    y2: float = 0.0
    cx: float = 0.5
    cy: float = 0.5
    fx: Optional[float] = None
    fy: Optional[float] = None
    r: float = 0.5

    @property
    def fallback_color(self) -> str:
        """Return the first stop color as a safe solid fallback."""
        if not self.stops:
            return "none"
        return self.stops[0].color


@dataclass
class FilterSpec:
    """Resolved SVG filter definition used by the writer layer."""

    filter_id: str
    kind: str
    primitive_chain: tuple[str, ...] = field(default_factory=tuple)
    dx: float = 0.0
    dy: float = 0.0
    blur: float = 0.0
    color: Optional[str] = None
    opacity: float = 1.0
    use_source_color: bool = False


# Global registries for gradient parsing.
_gradient_colors: dict[str, str] = {}
_gradient_specs: dict[str, GradientSpec] = {}
_filter_specs: dict[str, FilterSpec] = {}


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
    letter_spacing: Letter spacing in pixels.
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
    letter_spacing: float = 0.0
    text_anchor: str = "start"
    fill_gradient: Optional[GradientSpec] = None
    stroke_gradient: Optional[GradientSpec] = None
    filter_effect: Optional[FilterSpec] = None
    unsupported_styles: list[dict[str, str]] = field(default_factory=list)

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
            letter_spacing=self.letter_spacing,
            text_anchor=(
                self.text_anchor
                if self.text_anchor != "inherit"
                else parent.text_anchor
            ),
            fill_gradient=self.fill_gradient or parent.fill_gradient,
            stroke_gradient=self.stroke_gradient or parent.stroke_gradient,
            filter_effect=self.filter_effect,
        )

    @property
    def effective_fill_opacity(self) -> float:
        """Combined fill and overall opacity."""
        return self.fill_opacity * self.opacity

    @property
    def effective_stroke_opacity(self) -> float:
        """Combined stroke and overall opacity."""
        return self.stroke_opacity * self.opacity

    def clear_unsupported_style(self, property_name: str) -> None:
        """Remove inherited unsupported metadata for one property."""
        self.unsupported_styles = [
            item
            for item in self.unsupported_styles
            if item.get("property") != property_name
        ]

    def record_unsupported_style(
        self,
        property_name: str,
        value: str,
        reason: str,
    ) -> None:
        """Record a degraded style mapping for later diagnostics."""
        item = {
            "property": property_name,
            "value": value,
            "reason": reason,
        }
        if item not in self.unsupported_styles:
            self.unsupported_styles.append(item)


def clear_gradient_registry() -> None:
    """Clear the gradient color registry. Call before parsing a new SVG."""
    _gradient_colors.clear()
    _gradient_specs.clear()
    _filter_specs.clear()


def register_gradient_color(gradient_id: str, color: str) -> None:
    """
    Register a fallback color for a gradient.

    Args:
        gradient_id: The gradient/pattern ID (without #).
        color: The fallback color (hex format).
    """
    _gradient_colors[gradient_id] = color


def register_gradient(gradient: GradientSpec) -> None:
    """Register a resolved gradient definition and its fallback color."""
    _gradient_specs[gradient.gradient_id] = gradient
    if gradient.fallback_color != "none":
        register_gradient_color(gradient.gradient_id, gradient.fallback_color)


def get_gradient_color(gradient_id: str) -> Optional[str]:
    """
    Get the fallback color for a gradient.

    Args:
        gradient_id: The gradient/pattern ID (without #).

    Returns:
        The registered color or None if not found.
    """
    return _gradient_colors.get(gradient_id)


def get_gradient(gradient_id: str) -> Optional[GradientSpec]:
    """Get a resolved gradient definition by ID."""
    return _gradient_specs.get(gradient_id)


def register_filter(filter_spec: FilterSpec) -> None:
    """Register a resolved filter definition."""
    _filter_specs[filter_spec.filter_id] = filter_spec


def get_filter(filter_id: str) -> Optional[FilterSpec]:
    """Get a resolved filter definition by ID."""
    return _filter_specs.get(filter_id)


def parse_gradients_from_defs(defs_element) -> None:
    """
    Parse gradient definitions from a <defs> element and register their colors.

    Extracts the first stop color from each linearGradient or radialGradient
    and registers it as a fallback solid color.

    Args:
        defs_element: ElementTree element representing the <defs> section.
    """
    gradients: dict[str, object] = {}
    for child in defs_element:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        tag = tag.lower()
        if tag in ("lineargradient", "radialgradient"):
            grad_id = child.get("id")
            if grad_id:
                gradients[grad_id] = child

    resolved: dict[str, GradientSpec] = {}
    resolving: set[str] = set()
    for gradient_id in gradients:
        gradient = _resolve_gradient(gradient_id, gradients, resolved, resolving)
        if gradient is not None:
            register_gradient(gradient)


def parse_filters_from_defs(defs_element) -> None:
    """Parse filter definitions from a <defs> element and register supported chains."""
    for child in defs_element:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        if tag.lower() != "filter":
            continue

        filter_id = child.get("id")
        if not filter_id:
            continue

        filter_spec = _resolve_filter(child, filter_id)
        if filter_spec is not None:
            register_filter(filter_spec)


def _resolve_filter(filter_element, filter_id: str) -> FilterSpec:
    """Resolve a supported SVG filter chain into a writer-side effect contract."""
    primitives: list[tuple[str, object]] = []
    for child in filter_element:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        tag = tag.lower()
        if tag.startswith("fe"):
            primitives.append((tag, child))

    chain = tuple(tag for tag, _ in primitives)
    if chain == ("fedropshadow",):
        return _resolve_drop_shadow(filter_id, primitives[0][1], chain)
    if chain == (
        "fegaussianblur",
        "feoffset",
        "fecomponenttransfer",
        "femerge",
    ):
        return _resolve_shadow_chain(filter_id, primitives, chain)
    if chain == ("fegaussianblur", "fecomposite"):
        return _resolve_glow_chain(filter_id, primitives, chain)

    return FilterSpec(
        filter_id=filter_id,
        kind="unsupported",
        primitive_chain=chain,
    )


def _resolve_drop_shadow(filter_id: str, element, chain: tuple[str, ...]) -> FilterSpec:
    """Resolve SVG feDropShadow into a filter spec."""
    return FilterSpec(
        filter_id=filter_id,
        kind="outer_shadow",
        primitive_chain=chain,
        dx=_parse_filter_number(element.get("dx"), 0.0),
        dy=_parse_filter_number(element.get("dy"), 0.0),
        blur=_parse_filter_number(element.get("stdDeviation"), 0.0),
        color=parse_color(element.get("flood-color", "#000000")),
        opacity=_parse_filter_number(element.get("flood-opacity"), 1.0),
    )


def _resolve_shadow_chain(
    filter_id: str,
    primitives: list[tuple[str, object]],
    chain: tuple[str, ...],
) -> FilterSpec:
    """Resolve blur+offset+componentTransfer+merge into one outer shadow effect."""
    blur_node = primitives[0][1]
    offset_node = primitives[1][1]
    transfer_node = primitives[2][1]
    opacity = 0.18
    for child in transfer_node:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        if tag.lower() == "fefunca":
            opacity = _parse_filter_number(child.get("slope"), opacity)
            break

    return FilterSpec(
        filter_id=filter_id,
        kind="outer_shadow",
        primitive_chain=chain,
        dx=_parse_filter_number(offset_node.get("dx"), 0.0),
        dy=_parse_filter_number(offset_node.get("dy"), 0.0),
        blur=_parse_filter_number(blur_node.get("stdDeviation"), 0.0),
        color="#000000",
        opacity=opacity,
    )


def _resolve_glow_chain(
    filter_id: str,
    primitives: list[tuple[str, object]],
    chain: tuple[str, ...],
) -> FilterSpec:
    """Resolve blur+composite into a source-colored glow approximation."""
    blur_node = primitives[0][1]
    blur = _parse_filter_number(blur_node.get("stdDeviation"), 0.0)
    opacity = max(0.12, min(0.3, 1.2 / max(blur + 2.0, 2.0)))
    return FilterSpec(
        filter_id=filter_id,
        kind="glow",
        primitive_chain=chain,
        blur=blur,
        opacity=opacity,
        use_source_color=True,
    )


def _parse_filter_number(value: Optional[str], default: float) -> float:
    """Parse a numeric SVG filter parameter."""
    if value is None:
        return default
    raw = value.strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _resolve_gradient(
    gradient_id: str,
    gradients: dict[str, object],
    resolved: dict[str, GradientSpec],
    resolving: set[str],
) -> Optional[GradientSpec]:
    """Resolve one gradient definition, following href chains when present."""
    if gradient_id in resolved:
        return resolved[gradient_id]
    if gradient_id in resolving:
        return None

    element = gradients.get(gradient_id)
    if element is None:
        return None

    resolving.add(gradient_id)
    tag = element.tag
    if "}" in tag:
        tag = tag.split("}")[-1]
    kind = tag.lower().replace("gradient", "")

    href = (
        element.get("href")
        or element.get("{http://www.w3.org/1999/xlink}href")
        or ""
    ).strip()
    base_gradient = None
    if href.startswith("#"):
        base_gradient = _resolve_gradient(
            href[1:],
            gradients,
            resolved,
            resolving,
        )

    gradient = GradientSpec(
        gradient_id=gradient_id,
        kind=kind,
    )
    if base_gradient is not None:
        gradient = GradientSpec(
            gradient_id=gradient_id,
            kind=base_gradient.kind,
            stops=list(base_gradient.stops),
            x1=base_gradient.x1,
            y1=base_gradient.y1,
            x2=base_gradient.x2,
            y2=base_gradient.y2,
            cx=base_gradient.cx,
            cy=base_gradient.cy,
            fx=base_gradient.fx,
            fy=base_gradient.fy,
            r=base_gradient.r,
        )

    if gradient.kind == "linear":
        gradient.x1 = _parse_gradient_number(element.get("x1"), gradient.x1)
        gradient.y1 = _parse_gradient_number(element.get("y1"), gradient.y1)
        gradient.x2 = _parse_gradient_number(element.get("x2"), gradient.x2)
        gradient.y2 = _parse_gradient_number(element.get("y2"), gradient.y2)
    elif gradient.kind == "radial":
        gradient.cx = _parse_gradient_number(element.get("cx"), gradient.cx)
        gradient.cy = _parse_gradient_number(element.get("cy"), gradient.cy)
        gradient.fx = _parse_gradient_number(element.get("fx"), gradient.fx or gradient.cx)
        gradient.fy = _parse_gradient_number(element.get("fy"), gradient.fy or gradient.cy)
        gradient.r = _parse_gradient_number(element.get("r"), gradient.r)

    stops = _parse_gradient_stops(element)
    if stops:
        gradient.stops = stops

    if not gradient.stops:
        gradient.stops = [
            GradientStop(offset=0.0, color="#000000", opacity=1.0),
            GradientStop(offset=1.0, color="#000000", opacity=1.0),
        ]

    resolved[gradient_id] = gradient
    resolving.remove(gradient_id)
    return gradient


def _parse_gradient_number(value: Optional[str], default: float) -> float:
    """Parse objectBoundingBox gradient coordinates expressed as 0..1 or percent."""
    if value is None:
        return default

    raw = value.strip()
    if not raw:
        return default

    try:
        if raw.endswith("%"):
            return float(raw[:-1]) / 100.0
        return float(raw)
    except ValueError:
        return default


def _parse_gradient_stops(element) -> list[GradientStop]:
    """Parse stop nodes from one gradient definition."""
    stops: list[GradientStop] = []
    for stop in element:
        tag = stop.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        if tag.lower() != "stop":
            continue

        style_dict = parse_style_attribute(stop.get("style", ""))
        color_token = style_dict.get("stop-color", stop.get("stop-color", "#000000"))
        color = _parse_color_value(color_token)
        opacity_token = style_dict.get("stop-opacity", stop.get("stop-opacity", "1"))
        opacity = 1.0
        try:
            opacity = float(opacity_token)
        except ValueError:
            opacity = 1.0

        embedded_alpha = parse_color_alpha(color_token)
        if embedded_alpha is not None:
            opacity *= embedded_alpha

        offset = _parse_gradient_number(stop.get("offset"), 0.0)
        stops.append(
            GradientStop(
                offset=max(0.0, min(offset, 1.0)),
                color=color,
                opacity=max(0.0, min(opacity, 1.0)),
            )
        )

    return stops


def _parse_color_value(color_str: str) -> str:
    """
    Internal helper to parse a color value without url() handling.

    This avoids infinite recursion when parsing gradient stop colors.
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
        elif len(color_str) == 5:
            # Short hex with alpha (#rgba -> #rrggbb)
            return "#" + "".join(c * 2 for c in color_str[1:4])
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


def parse_color(color_str: str) -> str:
    """
    Parse an SVG/CSS color value.

    Args:
        color_str: Color string (hex, rgb(), named color, url(#gradient), or "none").

    Returns:
        Normalized hex color string (e.g., "#ff0000") or "none".
    """
    if not color_str:
        return "none"

    color_str_stripped = color_str.strip()
    color_str_lower = color_str_stripped.lower()

    # Handle special values
    if color_str_lower in ("none", "transparent", ""):
        return "none"
    if color_str_lower == "currentcolor":
        return "#000000"  # Default to black

    # Check for gradient/pattern url() references
    url_match = URL_REF_PATTERN.match(color_str_stripped)
    if url_match:
        ref_id = url_match.group(1)
        gradient_color = get_gradient_color(ref_id)
        if gradient_color:
            return gradient_color
        # Unknown reference, default to transparent/none
        return "none"

    # Named colors
    if color_str_lower in CSS_COLORS:
        return CSS_COLORS[color_str_lower]

    # Hex colors
    if color_str_lower.startswith("#"):
        if len(color_str_lower) == 4:
            # Short hex (#rgb -> #rrggbb)
            return "#" + "".join(c * 2 for c in color_str_lower[1:])
        elif len(color_str_lower) == 5:
            # Short hex with alpha (#rgba -> #rrggbb)
            return "#" + "".join(c * 2 for c in color_str_lower[1:4])
        elif len(color_str_lower) == 7:
            return color_str_lower
        elif len(color_str_lower) == 9:
            # #rrggbbaa - strip alpha
            return color_str_lower[:7]

    # rgb() format
    rgb_match = RGB_PATTERN.match(color_str_lower)
    if rgb_match:
        r, g, b = [int(x) for x in rgb_match.groups()]
        return f"#{r:02x}{g:02x}{b:02x}"

    # rgba() format
    rgba_match = RGBA_PATTERN.match(color_str_lower)
    if rgba_match:
        r, g, b = [int(x) for x in rgba_match.groups()[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"

    # Unknown format, return as-is
    return color_str_lower


def parse_color_alpha(color_str: str) -> Optional[float]:
    """
    Parse an alpha channel embedded in a CSS/SVG color token.

    Returns None when the color token does not carry its own alpha channel.
    """
    if not color_str:
        return None

    normalized = color_str.strip().lower()
    rgba_match = RGBA_PATTERN.match(normalized)
    if rgba_match:
        try:
            return max(0.0, min(float(rgba_match.group(4)), 1.0))
        except ValueError:
            return None

    if normalized.startswith("#"):
        if len(normalized) == 5:
            try:
                alpha = int(normalized[4] * 2, 16)
                return alpha / 255.0
            except ValueError:
                return None
        if len(normalized) == 9:
            try:
                alpha = int(normalized[7:9], 16)
                return alpha / 255.0
            except ValueError:
                return None

    return None


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
            letter_spacing=parent_style.letter_spacing,
            text_anchor=parent_style.text_anchor,
            fill_gradient=parent_style.fill_gradient,
            stroke_gradient=parent_style.stroke_gradient,
            unsupported_styles=list(parent_style.unsupported_styles),
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
        style.clear_unsupported_style("fill")
        style.fill_gradient = None
        style.fill = parse_color(fill_val)
        fill_alpha = parse_color_alpha(fill_val)
        if fill_alpha is not None:
            style.fill_opacity *= fill_alpha
        fill_ref = URL_REF_PATTERN.match(fill_val.strip())
        if fill_ref:
            gradient = get_gradient(fill_ref.group(1))
            if gradient is not None:
                style.fill_gradient = gradient
                style.fill = gradient.fallback_color
            else:
                style.record_unsupported_style(
                    "fill",
                    fill_val.strip(),
                    "unresolved-url-reference",
                )
        elif style.fill not in ("none",) and not style.fill.startswith("#"):
            style.record_unsupported_style(
                "fill",
                fill_val.strip(),
                "unparsed-color-token",
            )

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
        style.clear_unsupported_style("stroke")
        style.stroke_gradient = None
        style.stroke = parse_color(stroke_val)
        stroke_alpha = parse_color_alpha(stroke_val)
        if stroke_alpha is not None:
            style.stroke_opacity *= stroke_alpha
        stroke_ref = URL_REF_PATTERN.match(stroke_val.strip())
        if stroke_ref:
            gradient = get_gradient(stroke_ref.group(1))
            if gradient is not None:
                style.stroke_gradient = gradient
                style.stroke = gradient.fallback_color
                style.record_unsupported_style(
                    "stroke",
                    stroke_val.strip(),
                    "gradient-stroke-fallback",
                )
            else:
                style.record_unsupported_style(
                    "stroke",
                    stroke_val.strip(),
                    "unresolved-url-reference",
                )
        elif style.stroke not in ("none",) and not style.stroke.startswith("#"):
            style.record_unsupported_style(
                "stroke",
                stroke_val.strip(),
                "unparsed-color-token",
            )

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

    # Parse filter reference
    filter_val = get_attr("filter")
    if filter_val is not None:
        style.clear_unsupported_style("filter")
        filter_token = filter_val.strip()
        if filter_token.lower() == "none":
            style.filter_effect = None
        else:
            filter_ref = URL_REF_PATTERN.match(filter_token)
            if filter_ref:
                filter_spec = get_filter(filter_ref.group(1))
                if filter_spec is None:
                    style.filter_effect = None
                    style.record_unsupported_style(
                        "filter",
                        filter_token,
                        "unresolved-url-reference",
                    )
                else:
                    style.filter_effect = filter_spec
                    if filter_spec.kind == "unsupported":
                        style.record_unsupported_style(
                            "filter",
                            filter_token,
                            "unsupported-filter-chain",
                        )
            else:
                style.filter_effect = None
                style.record_unsupported_style(
                    "filter",
                    filter_token,
                    "unsupported-filter-token",
                )

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

    letter_spacing_val = get_attr("letter-spacing")
    if letter_spacing_val is not None:
        try:
            spacing_str = re.sub(
                r"[a-z%]+$", "", letter_spacing_val.strip(), flags=re.I
            )
            style.letter_spacing = float(spacing_str)
        except ValueError:
            pass

    text_anchor_val = get_attr("text-anchor")
    if text_anchor_val is not None:
        style.text_anchor = text_anchor_val

    return style
