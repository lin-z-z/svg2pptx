from __future__ import annotations

import json
from pathlib import Path

from svg2pptx import Config, convert_svg_inputs
from svg2pptx.cli import main


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_convert_svg_inputs_returns_structured_single_file_report(tmp_path):
    input_svg = tmp_path / "basic_shapes.svg"
    input_svg.write_text(
        (FIXTURES_DIR / "basic_shapes.svg").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    output_pptx = tmp_path / "out" / "basic_shapes.pptx"

    report = convert_svg_inputs(
        input_svg,
        output_pptx,
        config=Config(curve_tolerance=0.5),
    )

    assert report["status"] == "success"
    assert report["input"]["kind"] == "file"
    assert report["output"]["kind"] == "file"
    assert report["totals"]["success_count"] == 1
    assert report["config"]["curve_tolerance"] == 0.5
    assert output_pptx.exists()
    assert report["results"][0]["status"] == "success"
    assert report["results"][0]["output_path"].endswith("basic_shapes.pptx")


def test_convert_svg_inputs_directory_mode_preserves_recursive_structure(tmp_path):
    input_dir = tmp_path / "nested_svgs"
    nested = input_dir / "cards"
    nested.mkdir(parents=True)
    (nested / "grouped.svg").write_text(
        (FIXTURES_DIR / "grouped.svg").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_dir = tmp_path / "pptx_out"
    report = convert_svg_inputs(
        input_dir,
        output_dir,
        recursive=True,
    )

    assert report["status"] == "success"
    assert report["input"]["kind"] == "directory"
    assert report["totals"]["success_count"] == 1
    assert (output_dir / "cards" / "grouped.pptx").exists()
    assert report["results"][0]["output_path"].endswith("cards\\grouped.pptx")


def test_cli_writes_structured_report_json(tmp_path):
    input_dir = tmp_path / "svgs"
    input_dir.mkdir()
    (input_dir / "basic_shapes.svg").write_text(
        (FIXTURES_DIR / "basic_shapes.svg").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    output_dir = tmp_path / "pptx"
    report_path = tmp_path / "reports" / "batch.json"

    exit_code = main(
        [
            str(input_dir),
            str(output_dir),
            "--report-json",
            str(report_path),
            "--json",
        ]
    )

    assert exit_code == 0
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["status"] == "success"
    assert saved["totals"]["success_count"] == 1
    assert saved["results"][0]["status"] == "success"


def test_cli_error_path_is_structured(tmp_path):
    report_path = tmp_path / "missing.json"

    exit_code = main(
        [
            str(tmp_path / "does_not_exist.svg"),
            str(tmp_path / "out.pptx"),
            "--report-json",
            str(report_path),
            "--json",
        ]
    )

    assert exit_code == 1
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["status"] == "error"
    assert saved["totals"]["failure_count"] == 1
    assert "not found" in saved["error"]
