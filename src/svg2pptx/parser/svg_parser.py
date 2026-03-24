"""SVG document parsing and element traversal."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional, Union

from svg2pptx.parser.shapes import ParsedShape, parse_shape
from svg2pptx.parser.paths import PathShape, parse_path
from svg2pptx.parser.styles import (
    Style,
    parse_style,
    clear_gradient_registry,
    parse_gradients_from_defs,
)
from svg2pptx.parser.transforms import Transform, parse_transform
from svg2pptx.geometry.units import parse_length, parse_viewbox


# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"
NAMESPACES = {"svg": SVG_NS}


@dataclass
class SVGDocument:
    """
    Parsed SVG document structure.

    Attributes:
        width: Document width in pixels.
        height: Document height in pixels.
        viewbox: ViewBox tuple (min_x, min_y, width, height) or None.
        root_style: Root element style.
        elements: List of parsed elements (shapes, paths, groups, text).
    """

    width: float = 0.0
    height: float = 0.0
    viewbox: Optional[tuple[float, float, float, float]] = None
    root_style: Style = field(default_factory=Style)
    elements: list = field(default_factory=list)

    @property
    def scale_x(self) -> float:
        """X scale factor from viewBox to document size."""
        if self.viewbox and self.viewbox[2] > 0:
            return self.width / self.viewbox[2]
        return 1.0

    @property
    def scale_y(self) -> float:
        """Y scale factor from viewBox to document size."""
        if self.viewbox and self.viewbox[3] > 0:
            return self.height / self.viewbox[3]
        return 1.0

    @property
    def offset_x(self) -> float:
        """X offset from viewBox."""
        if self.viewbox:
            return -self.viewbox[0] * self.scale_x
        return 0.0

    @property
    def offset_y(self) -> float:
        """Y offset from viewBox."""
        if self.viewbox:
            return -self.viewbox[1] * self.scale_y
        return 0.0


@dataclass
class TextSpan:
    """
    Structured text span parsed from a <text> or <tspan> node.

    Attributes:
        text: Span text content.
        style: Effective text style for the span.
        x: Optional absolute x override.
        y: Optional absolute y override.
        dx: Relative x offset from the current text position.
        dy: Relative y offset from the current text position.
        source_kind: Source node type (text, tspan, or tail).
        source_index: Source order within the parent text node.
    """

    text: str
    style: Style = field(default_factory=Style)
    x: Optional[float] = None
    y: Optional[float] = None
    dx: float = 0.0
    dy: float = 0.0
    source_kind: str = "text"
    source_index: int = 0


@dataclass
class TextElement:
    """
    Parsed SVG text element.

    Attributes:
        text: Text content.
        x: X position.
        y: Y position.
        style: Text style.
        spans: Structured span list preserving tspan boundaries.
        transform: Element transform.
        element_id: Optional element ID.
    """

    text: str
    x: float = 0.0
    y: float = 0.0
    style: Style = field(default_factory=Style)
    spans: list[TextSpan] = field(default_factory=list)
    transform: Transform = field(default_factory=Transform.identity)
    element_id: Optional[str] = None


@dataclass
class GroupElement:
    """
    Parsed SVG group element.

    Attributes:
        children: List of child elements.
        style: Group style.
        transform: Group transform.
        element_id: Optional element ID.
    """

    children: list = field(default_factory=list)
    style: Style = field(default_factory=Style)
    transform: Transform = field(default_factory=Transform.identity)
    element_id: Optional[str] = None


class SVGParser:
    """
    Parser for SVG documents.

    Parses SVG files or strings and extracts shapes, paths, groups, and text.
    """

    def __init__(self, curve_tolerance: float = 1.0):
        """
        Initialize the SVG parser.

        Args:
            curve_tolerance: Tolerance for Bezier curve approximation.
        """
        self.curve_tolerance = curve_tolerance

    def parse_file(self, svg_path: Union[str, Path]) -> SVGDocument:
        """
        Parse an SVG file.

        Args:
            svg_path: Path to the SVG file.

        Returns:
            Parsed SVGDocument.
        """
        tree = ET.parse(str(svg_path))
        root = tree.getroot()
        return self._parse_root(root)

    def parse_string(self, svg_content: str) -> SVGDocument:
        """
        Parse an SVG string.

        Args:
            svg_content: SVG content as a string.

        Returns:
            Parsed SVGDocument.
        """
        root = ET.fromstring(svg_content)
        return self._parse_root(root)

    def _parse_root(self, root: ET.Element) -> SVGDocument:
        """Parse the root SVG element."""
        doc = SVGDocument()

        # Clear gradient registry before parsing new document
        clear_gradient_registry()

        # Parse dimensions
        width_attr = root.get("width", "")
        height_attr = root.get("height", "")

        # Parse viewBox
        viewbox_attr = root.get("viewBox", "")
        if viewbox_attr:
            try:
                doc.viewbox = parse_viewbox(viewbox_attr)
            except ValueError:
                pass

        # Determine dimensions
        if width_attr:
            try:
                doc.width = parse_length(width_attr)
            except ValueError:
                pass
        elif doc.viewbox:
            doc.width = doc.viewbox[2]

        if height_attr:
            try:
                doc.height = parse_length(height_attr)
            except ValueError:
                pass
        elif doc.viewbox:
            doc.height = doc.viewbox[3]

        # Parse gradient definitions from <defs> elements first
        for child in root:
            tag = child.tag
            if "}" in tag:
                tag = tag.split("}")[-1]
            if tag.lower() == "defs":
                parse_gradients_from_defs(child)

        # Parse root style
        doc.root_style = parse_style(root)

        # Parse child elements
        doc.elements = self._parse_children(
            root, doc.root_style, Transform.identity()
        )

        return doc

    def _parse_children(
        self,
        parent: ET.Element,
        parent_style: Style,
        parent_transform: Transform,
    ) -> list:
        """Parse child elements of a parent element."""
        elements = []

        for child in parent:
            element = self._parse_element(child, parent_style, parent_transform)
            if element is not None:
                elements.append(element)

        return elements

    def _parse_element(
        self,
        element: ET.Element,
        parent_style: Style,
        parent_transform: Transform,
    ) -> Optional[Union[ParsedShape, PathShape, GroupElement, TextElement]]:
        """Parse a single SVG element."""
        # Get tag name without namespace
        tag = element.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        tag = tag.lower()

        # Skip defs, style, and other non-renderable elements
        if tag in ("defs", "style", "metadata", "title", "desc", "symbol", "clippath", "mask"):
            return None

        # Parse transform
        local_transform = parse_transform(element.get("transform", ""))
        combined_transform = parent_transform.compose(local_transform)

        # Parse style with inheritance
        style = parse_style(element, parent_style)

        if tag == "g":
            # Group element
            children = self._parse_children(element, style, combined_transform)
            if not children:
                return None
            return GroupElement(
                children=children,
                style=style,
                transform=combined_transform,
                element_id=element.get("id"),
            )

        elif tag == "path":
            return parse_path(
                element,
                parent_style,
                parent_transform,
                self.curve_tolerance,
            )

        elif tag == "text":
            return self._parse_text(element, style, combined_transform)

        elif tag in ("rect", "circle", "ellipse", "line", "polygon", "polyline"):
            return parse_shape(element, parent_style, parent_transform)

        elif tag == "use":
            # TODO: Handle <use> elements by resolving references
            return None

        elif tag == "image":
            # TODO: Handle embedded images
            return None

        return None

    def _parse_text(
        self,
        element: ET.Element,
        style: Style,
        transform: Transform,
    ) -> Optional[TextElement]:
        """Parse a text element."""
        x = self._parse_optional_length(element.get("x"), default=0.0)
        y = self._parse_optional_length(element.get("y"), default=0.0)
        spans = self._collect_text_spans(element, style, x, y)
        if not spans:
            return None
        text_content = "".join(span.text for span in spans)

        return TextElement(
            text=text_content,
            x=x,
            y=y,
            style=style,
            spans=spans,
            transform=transform,
            element_id=element.get("id"),
        )

    def _collect_text_spans(
        self,
        element: ET.Element,
        parent_style: Style,
        default_x: float,
        default_y: float,
    ) -> list[TextSpan]:
        """Collect ordered text/tspan segments into structured spans."""
        spans: list[TextSpan] = []

        direct_text = self._normalize_text_segment(element.text)
        if direct_text is not None:
            spans.append(
                TextSpan(
                    text=direct_text,
                    style=parent_style,
                    x=self._parse_optional_length(element.get("x")),
                    y=self._parse_optional_length(element.get("y")),
                    dx=self._parse_optional_length(element.get("dx"), default=0.0),
                    dy=self._parse_optional_length(element.get("dy"), default=0.0),
                    source_kind="text",
                    source_index=0,
                )
            )

        tspan_index = 0
        for child in element:
            child_tag = child.tag
            if "}" in child_tag:
                child_tag = child_tag.split("}")[-1]
            child_tag = child_tag.lower()
            if child_tag != "tspan":
                continue

            child_style = parse_style(child, parent_style)
            child_text = self._normalize_text_segment(child.text)
            if child_text is not None:
                spans.append(
                    TextSpan(
                        text=child_text,
                        style=child_style,
                        x=self._parse_optional_length(child.get("x")),
                        y=self._parse_optional_length(child.get("y")),
                        dx=self._parse_optional_length(
                            child.get("dx"), default=0.0
                        ),
                        dy=self._parse_optional_length(
                            child.get("dy"), default=0.0
                        ),
                        source_kind="tspan",
                        source_index=tspan_index,
                    )
                )
                tspan_index += 1

            tail_text = self._normalize_text_segment(child.tail)
            if tail_text is not None:
                spans.append(
                    TextSpan(
                        text=tail_text,
                        style=parent_style,
                        x=default_x,
                        y=default_y,
                        source_kind="tail",
                        source_index=tspan_index,
                    )
                )
                tspan_index += 1

        return spans

    def _normalize_text_segment(self, value: Optional[str]) -> Optional[str]:
        """Drop indentation-only nodes while preserving visible text."""
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped

    def _parse_optional_length(
        self,
        value: Optional[str],
        default: Optional[float] = None,
    ) -> Optional[float]:
        """Parse an optional length-like attribute."""
        if value is None:
            return default
        try:
            return parse_length(value)
        except ValueError:
            return default
