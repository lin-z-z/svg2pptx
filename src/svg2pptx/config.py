"""Configuration options for SVG to PowerPoint conversion."""

from dataclasses import dataclass, field
from pptx.util import Inches


@dataclass
class Config:
    """
    Configuration settings for SVG to PowerPoint conversion.

    Attributes:
        slide_width: Width of the slide in EMU. Defaults to 13.333 inches (16:9).
        slide_height: Height of the slide in EMU. Defaults to 7.5 inches (16:9).
        scale: Scale factor applied to SVG content. Defaults to 1.0.
        offset_x: Horizontal offset in EMU for placing SVG content.
        offset_y: Vertical offset in EMU for placing SVG content.
        curve_tolerance: Tolerance for Bezier curve approximation.
            Lower values = more line segments = smoother curves.
            Defaults to 1.0.
        preserve_groups: Whether to maintain SVG group structure in PowerPoint.
            Defaults to False (shapes are ungrouped).
        flatten_groups: Whether to flatten all groups into individual shapes.
            Defaults to True (shapes are ungrouped for easier editing).
        default_fill: Default fill color for shapes without fill specified.
            Use "none" for transparent, or a hex color like "#000000".
        default_stroke: Default stroke color when not specified.
        default_stroke_width: Default stroke width in pixels when not specified.
        disable_shadows: Whether to disable shadows on generated shapes.
            Defaults to True.
        convert_text: Whether to convert text elements. Defaults to True.
        convert_shapes: Whether to convert shape elements. Defaults to True.
    """

    slide_width: int = Inches(13.333)
    slide_height: int = Inches(7.5)
    scale: float = 1.0
    offset_x: int = 0
    offset_y: int = 0
    curve_tolerance: float = 1.0
    preserve_groups: bool = False
    flatten_groups: bool = True
    default_fill: str = "none"
    default_stroke: str = "none"
    default_stroke_width: float = 1.0
    disable_shadows: bool = True
    convert_text: bool = True
    convert_shapes: bool = True
    # Guardrails stay comfortably above the current full_15 peaks: 57 / 61 / 41.
    max_shapes_per_page: int = 250
    max_freeform_points_per_page: int = 600
    max_points_per_freeform: int = 250
    unsupported_styles: list[dict[str, str]] = field(
        default_factory=list,
        repr=False,
    )
    gradient_stats: dict[str, int] = field(
        default_factory=lambda: {
            "linear_applied": 0,
            "radial_applied": 0,
            "degraded": 0,
        },
        repr=False,
    )
    render_metrics: dict[str, int] = field(
        default_factory=lambda: {
            "shape_count": 0,
            "freeform_points": 0,
            "max_points_single_shape": 0,
        },
        repr=False,
    )
    render_warnings: list[dict[str, object]] = field(
        default_factory=list,
        repr=False,
    )

    def reset_runtime_reports(self) -> None:
        """Clear per-conversion diagnostic output."""
        self.unsupported_styles.clear()
        self.gradient_stats = {
            "linear_applied": 0,
            "radial_applied": 0,
            "degraded": 0,
        }
        self.render_metrics = {
            "shape_count": 0,
            "freeform_points": 0,
            "max_points_single_shape": 0,
        }
        self.render_warnings.clear()

    def record_unsupported_style(
        self,
        property_name: str,
        value: str,
        reason: str,
        source: str = "",
    ) -> None:
        """Record a unique downgraded style item for diagnostics."""
        item = {
            "property": property_name,
            "value": value,
            "reason": reason,
        }
        if source:
            item["source"] = source
        if item not in self.unsupported_styles:
            self.unsupported_styles.append(item)

    def note_gradient_applied(self, kind: str) -> None:
        """Count a gradient fill that was emitted to DrawingML."""
        key = f"{kind}_applied"
        self.gradient_stats[key] = self.gradient_stats.get(key, 0) + 1

    def note_gradient_degraded(self) -> None:
        """Count a gradient that had to fall back or simplify."""
        self.gradient_stats["degraded"] = self.gradient_stats.get("degraded", 0) + 1

    def note_shape_created(self, shape_kind: str) -> None:
        """Track created PowerPoint shapes and warn on abnormal inflation."""
        self.render_metrics["shape_count"] += 1
        if self.render_metrics["shape_count"] > self.max_shapes_per_page:
            self.record_render_warning(
                "shape-count-overflow",
                "shape_count",
                self.render_metrics["shape_count"],
                self.max_shapes_per_page,
                source=shape_kind,
            )

    def note_freeform_points(self, points: int, source: str) -> None:
        """Track total freeform point usage and warn when thresholds are exceeded."""
        if points <= 0:
            return

        self.render_metrics["freeform_points"] += points
        self.render_metrics["max_points_single_shape"] = max(
            self.render_metrics["max_points_single_shape"],
            points,
        )
        if points > self.max_points_per_freeform:
            self.record_render_warning(
                "freeform-points-per-shape-overflow",
                "points",
                points,
                self.max_points_per_freeform,
                source=source,
            )
        if self.render_metrics["freeform_points"] > self.max_freeform_points_per_page:
            self.record_render_warning(
                "freeform-points-per-page-overflow",
                "freeform_points",
                self.render_metrics["freeform_points"],
                self.max_freeform_points_per_page,
                source=source,
            )

    def record_render_warning(
        self,
        code: str,
        metric: str,
        value: int,
        threshold: int,
        source: str = "",
    ) -> None:
        """Record one structured render warning without duplicating the same event."""
        warning = {
            "code": code,
            "metric": metric,
            "value": value,
            "threshold": threshold,
        }
        if source:
            warning["source"] = source
        if warning not in self.render_warnings:
            self.render_warnings.append(warning)

