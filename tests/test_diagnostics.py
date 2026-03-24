"""Tests for diagnostics and regression helper scripts."""

from __future__ import annotations

import json
from pathlib import Path

from svg2pptx import Config
from scripts.diag_svg2pptx import run_regression
from scripts.diag_svg_feature_scan import scan_svg_directory


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_scan_svg_directory_reports_expected_features(tmp_path):
    svg_dir = tmp_path / "scan_input"
    svg_dir.mkdir()
    (svg_dir / "sample.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="grad1"><stop offset="0%" stop-color="#fff"/></linearGradient>
          <filter id="shadow"></filter>
        </defs>
        <g transform="translate(10, 20)" opacity="0.8">
          <path d="M0 0 C 10 10, 20 10, 30 0" fill="url(#grad1)" />
          <text x="10" y="20">Hello<tspan dx="5">World</tspan></text>
          <rect x="0" y="0" width="10" height="10" filter="url(#missing-filter)" />
        </g>
        </svg>""",
        encoding="utf-8",
    )

    output_dir = tmp_path / "scan_output"
    summary = scan_svg_directory(svg_dir, output_dir, "unit_scan")

    assert summary["page_count"] == 1
    report = summary["pages"][0]
    assert report["metrics"]["transform_nodes"] == 1
    assert report["metrics"]["gradient_defs"] == 1
    assert report["metrics"]["filter_defs"] == 1
    assert report["metrics"]["text_nodes"] == 1
    assert report["metrics"]["tspan_nodes"] == 1
    assert report["metrics"]["curve_paths"] == 1
    assert report["metrics"]["unresolved_refs"] == 1
    assert "gradient" in report["risk_tags"]
    assert "curve_path" in report["risk_tags"]
    assert "unresolved_ref" in report["risk_tags"]
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "pages" / "sample.json").exists()
    assert summary["filter_support_summary"]["strategy_version"]


def test_scan_svg_directory_classifies_filter_support_levels(tmp_path):
    svg_dir = tmp_path / "scan_input"
    svg_dir.mkdir()
    (svg_dir / "filter_sample.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <defs>
          <filter id="shadow">
            <feGaussianBlur in="SourceAlpha" stdDeviation="8" />
            <feOffset dx="0" dy="4" result="offsetblur" />
            <feComponentTransfer><feFuncA type="linear" slope="0.2" /></feComponentTransfer>
            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect x="0" y="0" width="80" height="40" filter="url(#shadow)" />
        </svg>""",
        encoding="utf-8",
    )

    summary = scan_svg_directory(svg_dir)
    report = summary["pages"][0]
    filter_result = report["filters"][0]

    assert filter_result["filter_id"] == "shadow"
    assert filter_result["support_level"] == "approximate"
    assert filter_result["current_action"] == "ppt_outer_shadow"
    assert summary["filter_support_summary"]["support_levels"]["approximate"] == 1


def test_run_regression_creates_fixed_artifact_layout(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    for fixture_name in ("basic_shapes.svg", "grouped.svg"):
        (sample_dir / fixture_name).write_text(
            (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    run_dir, manifest = run_regression(sample_dir, tmp_path / "artifacts", "smoke")

    assert manifest["totals"]["page_count"] == 2
    assert manifest["totals"]["failure_count"] == 0
    assert (run_dir / "run.json").exists()
    assert (run_dir / "reports" / "svg_scan" / "summary.json").exists()
    assert (run_dir / "reports" / "manual_score.csv").exists()
    assert (run_dir / "reports" / "regression_report.md").exists()
    assert (run_dir / "pptx" / "basic_shapes.pptx").exists()
    assert (run_dir / "pptx" / "grouped.pptx").exists()

    saved_manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert saved_manifest["sample_set"] == "smoke"
    assert saved_manifest["unsupported_styles_summary"] == []
    assert "filter_support_summary" in saved_manifest
    assert "render_protection_summary" in saved_manifest


def test_run_regression_records_unsupported_style_items(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    (sample_dir / "style_fallback.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80">
        <defs>
          <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#ff0000" />
            <stop offset="100%" stop-color="#0000ff" />
          </linearGradient>
          <linearGradient id="grad2" href="#grad1" />
        </defs>
        <rect
          x="10"
          y="10"
          width="80"
          height="30"
          rx="12"
          ry="6"
          fill="url(#grad2)"
          stroke="#112233"
        />
        </svg>""",
        encoding="utf-8",
    )

    run_dir, manifest = run_regression(sample_dir, tmp_path / "artifacts", "style_fallback")

    assert manifest["gradient_support_summary"]["linear_applied"] == 1
    assert manifest["gradient_support_summary"]["degraded"] == 0
    reasons = {item["reason"] for item in manifest["unsupported_styles_summary"]}
    assert "non-uniform-radius-fallback" in reasons
    assert manifest["results"][0]["unsupported_styles"]
    assert manifest["results"][0]["gradient_stats"]["linear_applied"] == 1
    report = (run_dir / "reports" / "regression_report.md").read_text(encoding="utf-8")
    assert "不支持样式项" in report
    assert "Gradient 支持统计" in report


def test_run_regression_exposes_filter_page_results(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    (sample_dir / "filter_page.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        <rect x="10" y="10" width="60" height="20" fill="#0E5A8A" filter="url(#glow)" />
        </svg>""",
        encoding="utf-8",
    )

    run_dir, manifest = run_regression(sample_dir, tmp_path / "artifacts", "filter_page")

    assert manifest["filter_support_summary"]["support_levels"]["approximate"] == 1
    assert manifest["filter_page_results"][0]["filters"][0]["filter_id"] == "glow"
    assert manifest["filter_page_results"][0]["filters"][0]["current_action"] == "ppt_glow"
    report = (run_dir / "reports" / "regression_report.md").read_text(encoding="utf-8")
    assert "Filter 页结果" in report


def test_run_regression_records_render_protection_warnings(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    points = " ".join(f"{idx},{idx % 7}" for idx in range(90))
    (sample_dir / "dense_path.svg").write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120">
        <polyline points="{points}" fill="none" stroke="#0E5A8A" />
        </svg>""",
        encoding="utf-8",
    )

    config = Config(max_points_per_freeform=40, max_freeform_points_per_page=40)
    run_dir, manifest = run_regression(
        sample_dir,
        tmp_path / "artifacts",
        "dense_path",
        config=config,
    )

    assert manifest["render_protection_summary"]["warning_count"] >= 2
    warnings = manifest["results"][0]["render_warnings"]
    codes = {warning["code"] for warning in warnings}
    assert "freeform-points-per-shape-overflow" in codes
    assert "freeform-points-per-page-overflow" in codes
    report = (run_dir / "reports" / "regression_report.md").read_text(encoding="utf-8")
    assert "Render 保护统计" in report
