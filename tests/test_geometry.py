"""Tests for geometry utilities."""

import pytest
import math

from svg2pptx.geometry.units import px_to_emu, emu_to_px, parse_length, parse_viewbox
from svg2pptx.geometry.transforms import Transform, parse_transform, compose_transforms
from svg2pptx.geometry.curves import bezier_to_lines, svg_arc_to_lines


class TestUnits:
    """Tests for unit conversion."""

    def test_px_to_emu(self):
        # 1 px = 9525 EMU
        assert px_to_emu(1) == 9525
        assert px_to_emu(100) == 952500
        assert px_to_emu(0) == 0

    def test_emu_to_px(self):
        assert emu_to_px(9525) == 1.0
        assert emu_to_px(952500) == 100.0

    def test_round_trip(self):
        for px in [1, 10, 100, 500]:
            assert abs(emu_to_px(px_to_emu(px)) - px) < 0.001


class TestParseLength:
    """Tests for length parsing."""

    def test_no_unit(self):
        assert parse_length("100") == 100.0
        assert parse_length("50.5") == 50.5

    def test_px_unit(self):
        assert parse_length("100px") == 100.0
        assert parse_length("50.5px") == 50.5

    def test_pt_unit(self):
        # 1pt = 96/72 px = 1.333... px
        result = parse_length("72pt")
        assert abs(result - 96) < 0.001

    def test_in_unit(self):
        # 1in = 96 px
        assert parse_length("1in") == 96.0
        assert parse_length("2in") == 192.0

    def test_cm_unit(self):
        # 1cm = 96/2.54 px ≈ 37.8 px
        result = parse_length("2.54cm")
        assert abs(result - 96) < 0.1

    def test_mm_unit(self):
        # 10mm = 1cm
        result = parse_length("25.4mm")
        assert abs(result - 96) < 0.1

    def test_empty(self):
        assert parse_length("") == 0.0
        assert parse_length(None) == 0.0

    def test_percentage(self):
        assert parse_length("50%", reference_length=200) == 100.0
        assert parse_length("100%", reference_length=50) == 50.0


class TestParseViewbox:
    """Tests for viewBox parsing."""

    def test_space_separated(self):
        result = parse_viewbox("0 0 100 100")
        assert result == (0, 0, 100, 100)

    def test_comma_separated(self):
        result = parse_viewbox("0,0,100,100")
        assert result == (0, 0, 100, 100)

    def test_mixed_separators(self):
        result = parse_viewbox("10, 20 300 400")
        assert result == (10, 20, 300, 400)

    def test_float_values(self):
        result = parse_viewbox("0.5 0.5 99.5 99.5")
        assert result == (0.5, 0.5, 99.5, 99.5)

    def test_negative_values(self):
        result = parse_viewbox("-10 -10 120 120")
        assert result == (-10, -10, 120, 120)


class TestTransform:
    """Tests for Transform class."""

    def test_identity(self):
        t = Transform.identity()
        x, y = t.apply(10, 20)
        assert x == 10
        assert y == 20

    def test_translate(self):
        t = Transform.translate(5, 10)
        x, y = t.apply(10, 20)
        assert x == 15
        assert y == 30

    def test_scale(self):
        t = Transform.scale(2, 3)
        x, y = t.apply(10, 20)
        assert x == 20
        assert y == 60

    def test_scale_uniform(self):
        t = Transform.scale(2)
        x, y = t.apply(10, 20)
        assert x == 20
        assert y == 40

    def test_rotate_90(self):
        t = Transform.rotate(90)
        x, y = t.apply(10, 0)
        assert abs(x - 0) < 0.0001
        assert abs(y - 10) < 0.0001

    def test_rotate_180(self):
        t = Transform.rotate(180)
        x, y = t.apply(10, 20)
        assert abs(x - (-10)) < 0.0001
        assert abs(y - (-20)) < 0.0001

    def test_rotate_around_center(self):
        t = Transform.rotate(90, 50, 50)
        # Point (50, 0) rotated 90° around (50, 50) should be (100, 50)
        x, y = t.apply(50, 0)
        assert abs(x - 100) < 0.0001
        assert abs(y - 50) < 0.0001

    def test_compose(self):
        t1 = Transform.translate(10, 0)
        t2 = Transform.scale(2)
        # Compose: first translate, then scale
        composed = t1.compose(t2)
        # Apply t2 first, then t1
        # Actually, compose(other) applies other first, then self
        # So composed.apply(x, y) is equivalent to t1.apply(*t2.apply(x, y))
        x, y = composed.apply(5, 0)
        # t2.apply(5, 0) = (10, 0), t1.apply(10, 0) = (20, 0)
        assert x == 20
        assert y == 0


class TestBezierToLines:
    """Tests for Bezier curve approximation."""

    def test_straight_line(self):
        # A Bezier with control points on the line should produce minimal segments
        p0 = (0, 0)
        p1 = (33, 0)
        p2 = (66, 0)
        p3 = (100, 0)
        points = bezier_to_lines(p0, p1, p2, p3, tolerance=1.0)
        # Should end at the endpoint
        assert points[-1] == (100, 0)

    def test_curved_bezier(self):
        # A curved Bezier should produce multiple segments
        p0 = (0, 0)
        p1 = (0, 50)
        p2 = (100, 50)
        p3 = (100, 0)
        points = bezier_to_lines(p0, p1, p2, p3, tolerance=1.0)
        # Should have multiple points
        assert len(points) > 2
        # Should end at endpoint
        assert points[-1] == (100, 0)

    def test_tolerance_affects_segments(self):
        p0 = (0, 0)
        p1 = (0, 50)
        p2 = (100, 50)
        p3 = (100, 0)
        
        points_coarse = bezier_to_lines(p0, p1, p2, p3, tolerance=10.0)
        points_fine = bezier_to_lines(p0, p1, p2, p3, tolerance=0.5)
        
        # Fine tolerance should produce more points
        assert len(points_fine) >= len(points_coarse)


class TestSvgArcToLines:
    """Tests for SVG arc approximation."""

    def test_semicircle(self):
        # Arc from (0, 0) to (100, 0) with radius 50
        points = svg_arc_to_lines(
            x1=0, y1=0,
            rx=50, ry=50,
            x_axis_rotation=0,
            large_arc_flag=False,
            sweep_flag=True,
            x2=100, y2=0,
            tolerance=1.0
        )
        # Should have multiple points
        assert len(points) > 2
        # Should end at endpoint
        last = points[-1]
        assert abs(last[0] - 100) < 0.1
        assert abs(last[1] - 0) < 0.1

    def test_zero_radius(self):
        # Zero radius should return just the endpoint
        points = svg_arc_to_lines(
            x1=0, y1=0,
            rx=0, ry=0,
            x_axis_rotation=0,
            large_arc_flag=False,
            sweep_flag=True,
            x2=100, y2=0,
            tolerance=1.0
        )
        assert points == [(100, 0)]
