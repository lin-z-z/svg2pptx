"""Run svg2pptx regression exports with a fixed artifacts contract."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from svg2pptx import Config, svg_to_pptx  # noqa: E402
from diag_svg_feature_scan import scan_svg_directory  # noqa: E402

MANIFEST_PATH = REPO_ROOT / "tests" / "fixtures" / "oceanppt" / "manifest.json"
REPORT_TEMPLATE_PATH = REPO_ROOT / "docs" / "regression" / "report_template.md"
TIMESTAMP_FMT = "%Y-%m-%d_%H-%M-%S"


def _load_manifest_roles() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        return {}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    roles: dict[str, dict] = {}
    for sample_set in manifest.get("sample_sets", {}).values():
        for slide in sample_set.get("slides", []):
            roles[slide["file_name"]] = slide
    return roles


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_score_rows(svg_files: list[Path]) -> list[dict]:
    roles = _load_manifest_roles()
    rows: list[dict] = []
    for svg_file in svg_files:
        metadata = roles.get(svg_file.name, {})
        rows.append(
            {
                "sample_set": svg_file.parent.name,
                "page_id": svg_file.stem,
                "file_name": svg_file.name,
                "scenario_role": metadata.get("scenario_role", ""),
                "artifact_relpath": f"pptx/{svg_file.stem}.pptx",
                "layout_score": "",
                "text_score": "",
                "style_score": "",
                "hierarchy_score": "",
                "editability_score": "",
                "overall_score": "",
                "problem_types": "",
                "notes": "",
                "reviewer": "",
                "reviewed_at": "",
            }
        )
    return rows


def _render_report(run_dir: Path, sample_dir: Path, sample_set: str, summary: dict, results: list[dict]) -> None:
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    unsupported_summary = _summarize_unsupported_styles(results)
    gradient_summary = _summarize_gradient_stats(results)
    render_summary = _summarize_render_metrics(results)
    filter_summary = summary.get("filter_support_summary", {})
    filter_pages = [
        {
            "page_id": page["page_id"],
            "filters": page["filters"],
        }
        for page in summary.get("pages", [])
        if page.get("filters")
    ]
    report = (
        template.replace("{{sample_set}}", sample_set)
        .replace("{{generated_at}}", datetime.now(timezone.utc).isoformat())
        .replace("{{sample_dir}}", str(sample_dir))
        .replace("{{run_dir}}", str(run_dir))
        .replace("{{page_count}}", str(summary["page_count"]))
        .replace("{{success_count}}", str(sum(1 for item in results if item["status"] == "success")))
        .replace("{{failure_count}}", str(sum(1 for item in results if item["status"] != "success")))
        .replace("{{risk_distribution}}", json.dumps(summary["risk_distribution"], ensure_ascii=False, indent=2))
    )
    if unsupported_summary:
        report += (
            "\n\n## 不支持样式项\n\n```json\n"
            + json.dumps(unsupported_summary, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
    report += (
        "\n\n## Gradient 支持统计\n\n```json\n"
        + json.dumps(gradient_summary, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    report += (
        "\n\n## Render 保护统计\n\n```json\n"
        + json.dumps(render_summary, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    report += (
        "\n\n## Filter 支持统计\n\n```json\n"
        + json.dumps(filter_summary, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    if filter_pages:
        report += (
            "\n\n## Filter 页结果\n\n```json\n"
            + json.dumps(filter_pages, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
    (run_dir / "reports" / "regression_report.md").write_text(report, encoding="utf-8")


def _summarize_unsupported_styles(results: list[dict]) -> list[dict]:
    counts: dict[tuple[str, str, str, str], int] = {}
    for result in results:
        for item in result.get("unsupported_styles", []):
            key = (
                item.get("property", ""),
                item.get("reason", ""),
                item.get("value", ""),
                item.get("source", ""),
            )
            counts[key] = counts.get(key, 0) + 1

    summary: list[dict] = []
    for (property_name, reason, value, source), count in sorted(counts.items()):
        entry = {
            "property": property_name,
            "reason": reason,
            "value": value,
            "count": count,
        }
        if source:
            entry["source"] = source
        summary.append(entry)
    return summary


def _summarize_gradient_stats(results: list[dict]) -> dict:
    summary = {
        "linear_applied": 0,
        "radial_applied": 0,
        "degraded": 0,
    }
    for result in results:
        stats = result.get("gradient_stats", {})
        for key in summary:
            summary[key] += int(stats.get(key, 0))
    return summary


def _summarize_render_metrics(results: list[dict]) -> dict:
    summary = {
        "max_shape_count": 0,
        "max_freeform_points": 0,
        "max_points_single_shape": 0,
        "warning_count": 0,
        "pages_with_warnings": [],
    }
    for result in results:
        metrics = result.get("render_metrics", {})
        warnings = result.get("render_warnings", [])
        summary["max_shape_count"] = max(
            summary["max_shape_count"],
            int(metrics.get("shape_count", 0)),
        )
        summary["max_freeform_points"] = max(
            summary["max_freeform_points"],
            int(metrics.get("freeform_points", 0)),
        )
        summary["max_points_single_shape"] = max(
            summary["max_points_single_shape"],
            int(metrics.get("max_points_single_shape", 0)),
        )
        summary["warning_count"] += len(warnings)
        if warnings:
            summary["pages_with_warnings"].append(result["page_id"])
    return summary


def run_regression(
    sample_dir: Path,
    output_root: Path,
    sample_set: str | None = None,
    config: Config | None = None,
) -> tuple[Path, dict]:
    svg_files = sorted(sample_dir.glob("*.svg"))
    if not svg_files:
        raise ValueError(f"No SVG files found in {sample_dir}")

    sample_set_name = sample_set or sample_dir.name
    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)
    run_dir = output_root / f"{timestamp}_{sample_set_name}"
    reports_dir = run_dir / "reports"
    scan_dir = reports_dir / "svg_scan"
    pptx_dir = run_dir / "pptx"
    reports_dir.mkdir(parents=True, exist_ok=True)
    pptx_dir.mkdir(parents=True, exist_ok=True)

    summary = scan_svg_directory(sample_dir, scan_dir, sample_set_name)

    score_rows = _build_score_rows(svg_files)
    _write_csv(
        reports_dir / "manual_score.csv",
        [
            "sample_set",
            "page_id",
            "file_name",
            "scenario_role",
            "artifact_relpath",
            "layout_score",
            "text_score",
            "style_score",
            "hierarchy_score",
            "editability_score",
            "overall_score",
            "problem_types",
            "notes",
            "reviewer",
            "reviewed_at",
        ],
        score_rows,
    )

    results: list[dict] = []
    active_config = config or Config()
    for svg_file in svg_files:
        start = time.perf_counter()
        pptx_path = pptx_dir / f"{svg_file.stem}.pptx"
        active_config.reset_runtime_reports()
        try:
            svg_to_pptx(str(svg_file), str(pptx_path), config=active_config)
        except Exception as exc:  # pragma: no cover - exercised via manifest output
            results.append(
                {
                    "page_id": svg_file.stem,
                    "status": "error",
                    "output_relpath": str(pptx_path.relative_to(run_dir)),
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "error": str(exc),
                    "gradient_stats": dict(active_config.gradient_stats),
                    "render_metrics": dict(active_config.render_metrics),
                    "render_warnings": list(active_config.render_warnings),
                    "unsupported_styles": list(active_config.unsupported_styles),
                }
            )
        else:
            results.append(
                {
                    "page_id": svg_file.stem,
                    "status": "success",
                    "output_relpath": str(pptx_path.relative_to(run_dir)),
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "error": "",
                    "gradient_stats": dict(active_config.gradient_stats),
                    "render_metrics": dict(active_config.render_metrics),
                    "render_warnings": list(active_config.render_warnings),
                    "unsupported_styles": list(active_config.unsupported_styles),
                }
            )

    _render_report(run_dir, sample_dir, sample_set_name, summary, results)
    unsupported_summary = _summarize_unsupported_styles(results)
    gradient_summary = _summarize_gradient_stats(results)
    render_summary = _summarize_render_metrics(results)
    filter_summary = summary.get("filter_support_summary", {})
    filter_pages = [
        {
            "page_id": page["page_id"],
            "filters": page["filters"],
        }
        for page in summary.get("pages", [])
        if page.get("filters")
    ]

    run_manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_set": sample_set_name,
        "sample_dir": str(sample_dir),
        "run_dir": str(run_dir),
        "outputs": {
            "pptx_dir": str(pptx_dir),
            "scan_summary": str(scan_dir / "summary.json"),
            "manual_score": str(reports_dir / "manual_score.csv"),
            "report": str(reports_dir / "regression_report.md"),
        },
        "totals": {
            "page_count": len(svg_files),
            "success_count": sum(1 for item in results if item["status"] == "success"),
            "failure_count": sum(1 for item in results if item["status"] != "success"),
        },
        "gradient_support_summary": gradient_summary,
        "render_protection_summary": render_summary,
        "filter_support_summary": filter_summary,
        "filter_page_results": filter_pages,
        "unsupported_styles_summary": unsupported_summary,
        "results": results,
    }
    (run_dir / "run.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir, run_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run svg2pptx regression exports with a fixed artifacts layout.",
    )
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "oceanppt" / "full_15",
        help="Directory containing SVG samples.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "artifacts" / "regression_runs",
        help="Root directory for timestamped regression runs.",
    )
    parser.add_argument(
        "--sample-set",
        type=str,
        default=None,
        help="Logical sample set name.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    run_dir, manifest = run_regression(args.sample_dir, args.output_root, args.sample_set)
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "sample_set": manifest["sample_set"],
                "totals": manifest["totals"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
