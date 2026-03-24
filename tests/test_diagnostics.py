"""Tests for diagnostics and regression helper scripts."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_run_regression_records_unsupported_style_items(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    (sample_dir / "style_fallback.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80">
        <defs>
          <linearGradient id="grad1">
            <stop offset="0%" stop-color="#ff0000" />
            <stop offset="100%" stop-color="#0000ff" />
          </linearGradient>
        </defs>
        <rect
          x="10"
          y="10"
          width="80"
          height="30"
          rx="12"
          ry="6"
          fill="url(#grad1)"
          stroke="#112233"
        />
        </svg>""",
        encoding="utf-8",
    )

    run_dir, manifest = run_regression(sample_dir, tmp_path / "artifacts", "style_fallback")

    reasons = {item["reason"] for item in manifest["unsupported_styles_summary"]}
    assert "url-paint-fallback" in reasons
    assert "non-uniform-radius-fallback" in reasons
    assert manifest["results"][0]["unsupported_styles"]
    report = (run_dir / "reports" / "regression_report.md").read_text(encoding="utf-8")
    assert "不支持样式项" in report
