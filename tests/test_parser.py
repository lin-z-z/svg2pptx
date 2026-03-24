"""Tests for SVG parser module."""

import pytest
from pathlib import Path
from xml.etree.ElementTree import fromstring

from svg2pptx.parser.svg_parser import SVGParser, SVGDocument
from svg2pptx.parser.shapes import (
    parse_shape,
    RectShape,
    CircleShape,
    EllipseShape,
    LineShape,
    PolygonShape,
    PolylineShape,
    parse_points,
)
from svg2pptx.parser.styles import parse_style, parse_color, Style
from svg2pptx.parser.transforms import parse_transform, Transform


class TestParseColor:
    """Tests for color parsing."""

    def test_hex_color_full(self):
        assert parse_color("#ff0000") == "#ff0000"
        assert parse_color("#00FF00") == "#00ff00"

    def test_hex_color_short(self):
        assert parse_color("#f00") == "#ff0000"
        assert parse_color("#0F0") == "#00ff00"

    def test_named_color(self):
        assert parse_color("red") == "#ff0000"
        assert parse_color("blue") == "#0000ff"
        assert parse_color("BLACK") == "#000000"

    def test_rgb_color(self):
        assert parse_color("rgb(255, 0, 0)") == "#ff0000"
        assert parse_color("rgb(0, 128, 0)") == "#008000"

    def test_none_color(self):
        assert parse_color("none") == "none"
        assert parse_color("transparent") == "none"
        assert parse_color("") == "none"


class TestParseStyle:
    """Tests for style parsing."""

    def test_basic_style(self):
        element = fromstring('<rect fill="#ff0000" stroke="#0000ff" stroke-width="2"/>')
        style = parse_style(element)
        assert style.fill == "#ff0000"
        assert style.stroke == "#0000ff"
        assert style.stroke_width == 2.0

    def test_style_attribute(self):
        element = fromstring('<rect style="fill: red; stroke-width: 3px;"/>')
        style = parse_style(element)
        assert style.fill == "#ff0000"
        assert style.stroke_width == 3.0

    def test_opacity(self):
        element = fromstring('<rect fill="blue" opacity="0.5" fill-opacity="0.8"/>')
        style = parse_style(element)
        assert style.opacity == 0.5
        assert style.fill_opacity == 0.8
        assert style.effective_fill_opacity == 0.4  # 0.5 * 0.8

    def test_color_embedded_alpha_updates_fill_and_stroke_opacity(self):
        element = fromstring(
            '<rect fill="rgba(255, 0, 0, 0.25)" stroke="#00ff0080" />'
        )
        style = parse_style(element)
        assert style.fill == "#ff0000"
        assert style.fill_opacity == pytest.approx(0.25)
        assert style.stroke == "#00ff00"
        assert style.stroke_opacity == pytest.approx(128 / 255)

    def test_inherit_from_parent(self):
        parent_style = Style(fill="#ff0000", stroke="#0000ff", font_size=16.0)
        element = fromstring('<rect stroke-width="2"/>')
        style = parse_style(element, parent_style)
        assert style.fill == "#ff0000"  # Inherited
        assert style.stroke == "#0000ff"  # Inherited
        assert style.stroke_width == 2.0  # Overridden

    def test_letter_spacing(self):
        element = fromstring('<text letter-spacing="2">Hello</text>')
        style = parse_style(element)
        assert style.letter_spacing == 2.0

    def test_url_paint_records_unsupported_style(self):
        element = fromstring('<rect fill="url(#grad1)" stroke="url(#grad2)" />')
        style = parse_style(element)
        assert {
            "property": "fill",
            "value": "url(#grad1)",
            "reason": "unresolved-url-reference",
        } in style.unsupported_styles
        assert {
            "property": "stroke",
            "value": "url(#grad2)",
            "reason": "unresolved-url-reference",
        } in style.unsupported_styles

    def test_svg_parser_resolves_gradient_defs_and_href_chain(self):
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80">
            <defs>
                <linearGradient id="baseGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#112233" stop-opacity="0.2" />
                    <stop offset="100%" stop-color="#445566" />
                </linearGradient>
                <linearGradient id="derivedGrad" href="#baseGrad" />
            </defs>
            <rect x="0" y="0" width="100" height="40" fill="url(#derivedGrad)" />
        </svg>"""

        doc = SVGParser().parse_string(svg)
        shape = doc.elements[0]

        assert shape.style.fill_gradient is not None
        assert shape.style.fill_gradient.kind == "linear"
        assert shape.style.fill_gradient.x2 == pytest.approx(1.0)
        assert len(shape.style.fill_gradient.stops) == 2
        assert shape.style.fill_gradient.stops[0].color == "#112233"
        assert shape.style.fill_gradient.stops[0].opacity == pytest.approx(0.2)
        assert shape.style.unsupported_styles == []


class TestParseTransform:
    """Tests for transform parsing."""

    def test_translate(self):
        t = parse_transform("translate(10, 20)")
        assert t.e == 10
        assert t.f == 20

    def test_translate_single_value(self):
        t = parse_transform("translate(10)")
        assert t.e == 10
        assert t.f == 0

    def test_scale(self):
        t = parse_transform("scale(2)")
        assert t.a == 2
        assert t.d == 2

    def test_scale_non_uniform(self):
        t = parse_transform("scale(2, 3)")
        assert t.a == 2
        assert t.d == 3

    def test_rotate(self):
        import math
        t = parse_transform("rotate(90)")
        # 90 degree rotation
        assert abs(t.a - 0) < 0.0001
        assert abs(t.b - 1) < 0.0001
        assert abs(t.c - (-1)) < 0.0001
        assert abs(t.d - 0) < 0.0001

    def test_matrix(self):
        t = parse_transform("matrix(1, 0, 0, 1, 10, 20)")
        assert t.a == 1
        assert t.b == 0
        assert t.c == 0
        assert t.d == 1
        assert t.e == 10
        assert t.f == 20

    def test_multiple_transforms(self):
        t = parse_transform("translate(10, 0) scale(2)")
        x, y = t.apply(5, 0)
        assert x == 30
        assert y == 0

    def test_translate_then_rotate_uses_svg_order(self):
        t = parse_transform("translate(100, 100) rotate(45)")
        x, y = t.apply(0, 0)
        assert abs(x - 0) < 0.0001
        assert abs(y - 141.4213562373) < 0.0001


class TestParsePoints:
    """Tests for polygon/polyline points parsing."""

    def test_comma_separated(self):
        points = parse_points("100,200 300,400")
        assert points == [(100, 200), (300, 400)]

    def test_space_separated(self):
        points = parse_points("100 200 300 400")
        assert points == [(100, 200), (300, 400)]

    def test_mixed_separators(self):
        points = parse_points("100,200,300,400")
        assert points == [(100, 200), (300, 400)]

    def test_empty(self):
        assert parse_points("") == []
        assert parse_points(None) == []


class TestParseShape:
    """Tests for shape parsing."""

    def test_parse_rect(self):
        element = fromstring('<rect x="10" y="20" width="100" height="50"/>')
        shape = parse_shape(element)
        assert isinstance(shape, RectShape)
        assert shape.x == 10
        assert shape.y == 20
        assert shape.width == 100
        assert shape.height == 50

    def test_parse_rect_with_radius(self):
        element = fromstring('<rect x="0" y="0" width="100" height="50" rx="5" ry="10"/>')
        shape = parse_shape(element)
        assert shape.rx == 5
        assert shape.ry == 10

    def test_parse_circle(self):
        element = fromstring('<circle cx="50" cy="50" r="25"/>')
        shape = parse_shape(element)
        assert isinstance(shape, CircleShape)
        assert shape.cx == 50
        assert shape.cy == 50
        assert shape.r == 25

    def test_parse_ellipse(self):
        element = fromstring('<ellipse cx="50" cy="50" rx="30" ry="20"/>')
        shape = parse_shape(element)
        assert isinstance(shape, EllipseShape)
        assert shape.rx == 30
        assert shape.ry == 20

    def test_parse_line(self):
        element = fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        shape = parse_shape(element)
        assert isinstance(shape, LineShape)
        assert shape.x1 == 0
        assert shape.y1 == 0
        assert shape.x2 == 100
        assert shape.y2 == 100

    def test_parse_polygon(self):
        element = fromstring('<polygon points="0,0 100,0 50,100"/>')
        shape = parse_shape(element)
        assert isinstance(shape, PolygonShape)
        assert len(shape.points) == 3

    def test_parse_polyline(self):
        element = fromstring('<polyline points="0,0 50,50 100,0"/>')
        shape = parse_shape(element)
        assert isinstance(shape, PolylineShape)
        assert len(shape.points) == 3


class TestSVGParser:
    """Tests for the main SVG parser."""

    def test_parse_simple_svg(self):
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <rect x="10" y="10" width="80" height="80" fill="red"/>
        </svg>'''
        parser = SVGParser()
        doc = parser.parse_string(svg)
        
        assert doc.width == 100
        assert doc.height == 100
        assert len(doc.elements) == 1
        assert isinstance(doc.elements[0], RectShape)

    def test_parse_viewbox(self):
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" 
                     width="200" height="200" viewBox="0 0 100 100">
            <rect x="0" y="0" width="100" height="100"/>
        </svg>'''
        parser = SVGParser()
        doc = parser.parse_string(svg)
        
        assert doc.width == 200
        assert doc.height == 200
        assert doc.viewbox == (0, 0, 100, 100)
        assert doc.scale_x == 2.0
        assert doc.scale_y == 2.0

    def test_parse_group(self):
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <g id="mygroup">
                <rect x="0" y="0" width="50" height="50"/>
                <circle cx="75" cy="75" r="20"/>
            </g>
        </svg>'''
        parser = SVGParser()
        doc = parser.parse_string(svg)
        
        assert len(doc.elements) == 1
        group = doc.elements[0]
        assert len(group.children) == 2

    def test_parse_text_spans_preserves_tspan_structure(self):
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
            <text x="100" y="200" font-family="Noto Sans SC" font-size="32" letter-spacing="2">
                5-10<tspan font-size="48" font-weight="bold" dx="8">x</tspan>
            </text>
        </svg>'''
        parser = SVGParser()
        doc = parser.parse_string(svg)

        text = doc.elements[0]
        assert text.text == "5-10x"
        assert len(text.spans) == 2
        assert text.spans[0].text == "5-10"
        assert text.spans[0].x == 100
        assert text.spans[0].y == 200
        assert text.spans[0].style.font_family == "Noto Sans SC"
        assert text.spans[0].style.letter_spacing == 2.0
        assert text.spans[1].text == "x"
        assert text.spans[1].dx == 8
        assert text.spans[1].style.font_size == 48.0
        assert text.spans[1].style.font_weight == "bold"
        assert text.spans[1].source_kind == "tspan"

    def test_parse_text_spans_from_oceanppt_fixture(self):
        svg_path = (
            Path(__file__).parent
            / "fixtures"
            / "oceanppt"
            / "baseline_5"
            / "slide_008.svg"
        )
        parser = SVGParser()
        doc = parser.parse_file(svg_path)

        def collect_text_elements(elements):
            found = []
            for element in elements:
                if hasattr(element, "spans"):
                    found.append(element)
                if hasattr(element, "children"):
                    found.extend(collect_text_elements(element.children))
            return found

        text_elements = collect_text_elements(doc.elements)
        multi_span = next(
            (
                element
                for element in text_elements
                if len(element.spans) >= 3 and "景区空中观光定制化路径" in element.text
            ),
            None,
        )

        assert multi_span is not None
        assert [span.text for span in multi_span.spans] == [
            "· 景区空中观光定制化路径",
            "· 高端飞行社交与驾驶体验",
            "· 重新定义城市天际线视野",
        ]
        assert [span.dy for span in multi_span.spans] == [0.0, 30.0, 30.0]
        assert all(span.source_kind == "tspan" for span in multi_span.spans)

    def test_oceanppt_text_pages_do_not_parse_empty(self):
        parser = SVGParser()

        def collect_text_elements(elements):
            found = []
            for element in elements:
                if hasattr(element, "spans"):
                    found.append(element)
                if hasattr(element, "children"):
                    found.extend(collect_text_elements(element.children))
            return found

        fixture_dirs = [
            Path(__file__).parent / "fixtures" / "oceanppt" / "baseline_5",
            Path(__file__).parent / "fixtures" / "oceanppt" / "full_15",
        ]

        for fixture_dir in fixture_dirs:
            for svg_path in sorted(fixture_dir.glob("*.svg")):
                raw_svg = svg_path.read_text(encoding="utf-8")
                if "<text" not in raw_svg:
                    continue
                doc = parser.parse_file(svg_path)
                text_elements = collect_text_elements(doc.elements)
                assert text_elements, f"{svg_path.name} lost all text elements"
                assert all(
                    element.text.strip() for element in text_elements
                ), f"{svg_path.name} contains empty parsed text elements"
