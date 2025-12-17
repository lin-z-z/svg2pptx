"""Unit conversion utilities for SVG to PowerPoint conversion."""

import re
from typing import Optional

# EMU (English Metric Units) constants
EMU_PER_INCH = 914400
EMU_PER_PT = 12700  # 1 point = 1/72 inch
EMU_PER_CM = 360000  # 1 cm = 360000 EMU
EMU_PER_MM = 36000  # 1 mm = 36000 EMU

# Default DPI for SVG (CSS pixels)
DEFAULT_DPI = 96
EMU_PER_PX = EMU_PER_INCH // DEFAULT_DPI  # 9525 EMU per pixel

# Regex for parsing length values with units
LENGTH_PATTERN = re.compile(
    r"^\s*(-?[\d.]+)\s*(px|pt|in|cm|mm|em|ex|%|)?\s*$", re.IGNORECASE
)


def px_to_emu(px: float) -> int:
    """
    Convert CSS pixels to EMU.

    Args:
        px: Value in CSS pixels.

    Returns:
        Value in EMU (rounded to integer).
    """
    return int(px * EMU_PER_PX)


def emu_to_px(emu: int) -> float:
    """
    Convert EMU to CSS pixels.

    Args:
        emu: Value in EMU.

    Returns:
        Value in CSS pixels.
    """
    return emu / EMU_PER_PX


def parse_length(
    value: str,
    reference_length: Optional[float] = None,
    font_size: float = 16.0,
) -> float:
    """
    Parse an SVG length value and return pixels.

    Supports units: px, pt, in, cm, mm, em, ex, %
    If no unit is specified, assumes pixels.

    Args:
        value: SVG length string (e.g., "100px", "2.5in", "50%").
        reference_length: Reference length for percentage calculations.
        font_size: Font size in pixels for em/ex calculations.

    Returns:
        Length in CSS pixels.

    Raises:
        ValueError: If the length string is invalid.
    """
    if value is None:
        return 0.0

    value = str(value).strip()
    if not value:
        return 0.0

    match = LENGTH_PATTERN.match(value)
    if not match:
        raise ValueError(f"Invalid length value: {value}")

    number = float(match.group(1))
    unit = (match.group(2) or "").lower()

    if unit == "" or unit == "px":
        return number
    elif unit == "pt":
        return number * (DEFAULT_DPI / 72)
    elif unit == "in":
        return number * DEFAULT_DPI
    elif unit == "cm":
        return number * (DEFAULT_DPI / 2.54)
    elif unit == "mm":
        return number * (DEFAULT_DPI / 25.4)
    elif unit == "em":
        return number * font_size
    elif unit == "ex":
        return number * font_size * 0.5  # Approximate ex as 0.5em
    elif unit == "%":
        if reference_length is None:
            raise ValueError("Percentage requires reference_length")
        return number / 100.0 * reference_length
    else:
        raise ValueError(f"Unknown unit: {unit}")


def parse_viewbox(viewbox_str: str) -> tuple[float, float, float, float]:
    """
    Parse SVG viewBox attribute.

    Args:
        viewbox_str: viewBox attribute value (e.g., "0 0 100 100").

    Returns:
        Tuple of (min_x, min_y, width, height).

    Raises:
        ValueError: If viewBox format is invalid.
    """
    if not viewbox_str:
        raise ValueError("Empty viewBox")

    parts = re.split(r"[\s,]+", viewbox_str.strip())
    if len(parts) != 4:
        raise ValueError(f"Invalid viewBox format: {viewbox_str}")

    try:
        return tuple(float(p) for p in parts)  # type: ignore
    except ValueError as e:
        raise ValueError(f"Invalid viewBox values: {viewbox_str}") from e
