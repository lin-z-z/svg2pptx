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
class TextElement:
    """
    Parsed SVG text element.

    Attributes:
        text: Text content.
        x: X position.
        y: Y position.
        style: Text style.
        transform: Element transform.
        element_id: Optional element ID.
    """

    text: str
    x: float = 0.0
    y: float = 0.0
    style: Style = field(default_factory=Style)
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
        # Get text content (including from tspan children)
        text_parts = []

        # Direct text content
        if element.text:
            text_parts.append(element.text)

        # Text from tspan children
        for child in element:
            child_tag = child.tag
            if "}" in child_tag:
                child_tag = child_tag.split("}")[-1]
            if child_tag.lower() == "tspan":
                if child.text:
                    text_parts.append(child.text)
                if child.tail:
                    text_parts.append(child.tail)

        text_content = "".join(text_parts).strip()
        if not text_content:
            return None

        # Parse position
        x = 0.0
        y = 0.0
        x_attr = element.get("x")
        y_attr = element.get("y")
        if x_attr:
            try:
                x = parse_length(x_attr)
            except ValueError:
                pass
        if y_attr:
            try:
                y = parse_length(y_attr)
            except ValueError:
                pass

        return TextElement(
            text=text_content,
            x=x,
            y=y,
            style=style,
            transform=transform,
            element_id=element.get("id"),
        )
