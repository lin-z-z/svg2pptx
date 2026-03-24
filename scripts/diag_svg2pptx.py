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
from svg2pptx.result_status import classify_page_result, summarize_page_statuses  # noqa: E402
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


def _render_report(run_dir: Path, sample_dir: Path, sample_set: str, summary: dict, results: list[dict], manifest: dict) -> None:
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    unsupported_summary = manifest["unsupported_styles_summary"]
    gradient_summary = manifest["gradient_support_summary"]
    render_summary = manifest["render_protection_summary"]
    filter_summary = manifest["filter_support_summary"]
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
        "\n\n## 产物路径\n\n```json\n"
        + json.dumps(manifest["outputs"], ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    report += (
        "\n\n## 问题分级\n\n```json\n"
        + json.dumps(manifest["problem_summary"], ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    report += (
        "\n\n## 页面状态与失败码\n\n```json\n"
        + json.dumps(manifest["page_result_summary"], ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    report += (
        "\n\n## 关键指标\n\n```json\n"
        + json.dumps(manifest["key_metrics"], ensure_ascii=False, indent=2)
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
    comparison = manifest.get("comparison", {})
    if comparison.get("available"):
        report += (
            "\n\n## 与上次回归对比\n\n```json\n"
            + json.dumps(comparison, ensure_ascii=False, indent=2)
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


def _summarize_problem_levels(summary: dict, results: list[dict]) -> dict:
    pages_by_id = {
        page["page_id"]: page
        for page in summary.get("pages", [])
    }
    level_counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "clean": 0,
    }
    pages: list[dict] = []

    for result in results:
        page = pages_by_id.get(result["page_id"], {})
        support_levels = sorted(
            {
                item.get("support_level", "")
                for item in page.get("filters", [])
                if item.get("support_level")
            }
        )
        reasons: list[str] = []
        if result["status"] != "success":
            level = "high"
            reasons.append("conversion-error")
        elif result.get("render_warnings") or any(
            level in {"controlled_degradation", "unsupported"}
            for level in support_levels
        ):
            level = "medium"
            if result.get("render_warnings"):
                reasons.append("render-warning")
            if any(
                level in {"controlled_degradation", "unsupported"}
                for level in support_levels
            ):
                reasons.append("filter-degradation")
        elif result.get("unsupported_styles") or support_levels:
            level = "low"
            if result.get("unsupported_styles"):
                reasons.append("unsupported-style")
            if support_levels:
                reasons.append("filter-approximation")
        else:
            level = "clean"
            reasons.append("clean")

        level_counts[level] += 1
        page_summary = {
            "page_id": result["page_id"],
            "level": level,
            "reasons": reasons,
            "duration_ms": result["duration_ms"],
        }
        if level != "clean":
            page_summary["risk_tags"] = page.get("risk_tags", [])
        pages.append(page_summary)

    return {
        "counts": level_counts,
        "pages": [page for page in pages if page["level"] != "clean"],
    }


def _classify_results(summary: dict, results: list[dict]) -> list[dict]:
    pages_by_id = {
        page["page_id"]: page
        for page in summary.get("pages", [])
    }
    classified: list[dict] = []
    for result in results:
        page = pages_by_id.get(result["page_id"], {})
        classification = classify_page_result(
            error=result.get("error", ""),
            render_warnings=result.get("render_warnings", []),
            unsupported_styles=result.get("unsupported_styles", []),
            filter_results=page.get("filters", []),
            risk_tags=page.get("risk_tags", []),
        )
        enriched = dict(result)
        enriched.update(classification)
        classified.append(enriched)
    return classified


def _summarize_key_metrics(run_dir: Path, results: list[dict]) -> dict:
    durations = [float(result.get("duration_ms", 0)) for result in results]
    render_warning_total = sum(len(result.get("render_warnings", [])) for result in results)
    unsupported_total = sum(len(result.get("unsupported_styles", [])) for result in results)
    output_sizes: list[tuple[str, int]] = []
    for result in results:
        output_path = run_dir / result["output_relpath"]
        if output_path.exists():
            output_sizes.append((result["page_id"], output_path.stat().st_size))
        else:
            output_sizes.append((result["page_id"], 0))

    slowest_page = max(
        ((result["page_id"], float(result.get("duration_ms", 0))) for result in results),
        key=lambda item: item[1],
    )
    largest_output_page = max(output_sizes, key=lambda item: item[1])

    return {
        "duration_ms_total": round(sum(durations), 2),
        "duration_ms_avg": round(sum(durations) / len(durations), 2),
        "duration_ms_max": round(slowest_page[1], 2),
        "slowest_page": {
            "page_id": slowest_page[0],
            "duration_ms": round(slowest_page[1], 2),
        },
        "pptx_size_total_bytes": sum(size for _, size in output_sizes),
        "pptx_size_max_bytes": largest_output_page[1],
        "largest_output_page": {
            "page_id": largest_output_page[0],
            "size_bytes": largest_output_page[1],
        },
        "unsupported_style_item_count": unsupported_total,
        "pages_with_unsupported_styles": [
            result["page_id"]
            for result in results
            if result.get("unsupported_styles")
        ],
        "render_warning_count": render_warning_total,
        "pages_with_render_warnings": [
            result["page_id"]
            for result in results
            if result.get("render_warnings")
        ],
    }


def _extract_comparison_metrics(manifest: dict) -> dict:
    totals = manifest.get("totals", {})
    key_metrics = manifest.get("key_metrics", {})
    render_summary = manifest.get("render_protection_summary", {})
    problem_counts = manifest.get("problem_summary", {}).get("counts", {})
    return {
        "failure_count": int(totals.get("failure_count", 0)),
        "success_count": int(totals.get("success_count", 0)),
        "duration_ms_total": float(key_metrics.get("duration_ms_total", 0)),
        "pptx_size_total_bytes": int(key_metrics.get("pptx_size_total_bytes", 0)),
        "render_warning_count": int(key_metrics.get("render_warning_count", 0)),
        "unsupported_style_item_count": int(
            key_metrics.get("unsupported_style_item_count", 0)
        ),
        "max_shape_count": int(render_summary.get("max_shape_count", 0)),
        "max_freeform_points": int(render_summary.get("max_freeform_points", 0)),
        "high_problem_pages": int(problem_counts.get("high", 0)),
        "medium_problem_pages": int(problem_counts.get("medium", 0)),
    }


def _build_comparison(current_manifest: dict, previous_manifest: dict, previous_path: Path) -> dict:
    current_metrics = _extract_comparison_metrics(current_manifest)
    previous_metrics = _extract_comparison_metrics(previous_manifest)
    deltas = {
        key: current_metrics[key] - previous_metrics.get(key, 0)
        for key in current_metrics
    }
    return {
        "available": True,
        "previous_run_json": str(previous_path),
        "previous_run_dir": previous_manifest.get("run_dir", ""),
        "current_metrics": current_metrics,
        "previous_metrics": previous_metrics,
        "delta": deltas,
    }


def _load_run_manifest(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_previous_run_manifest(output_root: Path, sample_set: str) -> Path | None:
    candidates = sorted(
        output_root.glob(f"*_{sample_set}/run.json"),
        key=lambda item: item.parent.name,
    )
    return candidates[-1] if candidates else None


def _allocate_run_dir(output_root: Path, sample_set: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)
    base_name = f"{timestamp}_{sample_set}"
    run_dir = output_root / base_name
    suffix = 1
    while run_dir.exists():
        run_dir = output_root / f"{base_name}-{suffix:02d}"
        suffix += 1
    return run_dir


def run_regression(
    sample_dir: Path,
    output_root: Path,
    sample_set: str | None = None,
    config: Config | None = None,
    compare_to: Path | None = None,
) -> tuple[Path, dict]:
    svg_files = sorted(sample_dir.glob("*.svg"))
    if not svg_files:
        raise ValueError(f"No SVG files found in {sample_dir}")

    sample_set_name = sample_set or sample_dir.name
    run_dir = _allocate_run_dir(output_root, sample_set_name)
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

    results = _classify_results(summary, results)
    unsupported_summary = _summarize_unsupported_styles(results)
    gradient_summary = _summarize_gradient_stats(results)
    render_summary = _summarize_render_metrics(results)
    page_result_summary = summarize_page_statuses(results)
    problem_summary = _summarize_problem_levels(summary, results)
    key_metrics = _summarize_key_metrics(run_dir, results)
    filter_summary = summary.get("filter_support_summary", {})
    filter_pages = [
        {
            "page_id": page["page_id"],
            "filters": page["filters"],
        }
        for page in summary.get("pages", [])
        if page.get("filters")
    ]
    outputs = {
        "pptx_dir": str(pptx_dir),
        "scan_summary": str(scan_dir / "summary.json"),
        "manual_score": str(reports_dir / "manual_score.csv"),
        "report": str(reports_dir / "regression_report.md"),
    }

    run_manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_set": sample_set_name,
        "sample_dir": str(sample_dir),
        "run_dir": str(run_dir),
        "outputs": outputs,
        "totals": {
            "page_count": len(svg_files),
            "success_count": sum(1 for item in results if item["status"] == "success"),
            "failure_count": sum(1 for item in results if item["status"] != "success"),
        },
        "gradient_support_summary": gradient_summary,
        "page_result_summary": page_result_summary,
        "problem_summary": problem_summary,
        "key_metrics": key_metrics,
        "render_protection_summary": render_summary,
        "filter_support_summary": filter_summary,
        "filter_page_results": filter_pages,
        "unsupported_styles_summary": unsupported_summary,
        "results": results,
    }
    previous_manifest = _load_run_manifest(compare_to)
    if previous_manifest is not None and compare_to is not None:
        run_manifest["comparison"] = _build_comparison(
            run_manifest,
            previous_manifest,
            compare_to,
        )
    else:
        run_manifest["comparison"] = {
            "available": False,
        }
    _render_report(run_dir, sample_dir, sample_set_name, summary, results, run_manifest)
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
    parser.add_argument(
        "--compare-to",
        type=Path,
        default=None,
        help="Previous run.json to compare against.",
    )
    parser.add_argument(
        "--compare-last",
        action="store_true",
        help="Compare with the latest run.json under output-root for the same sample set.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    sample_set_name = args.sample_set or args.sample_dir.name
    compare_to = args.compare_to
    if compare_to is None and args.compare_last:
        compare_to = _find_previous_run_manifest(args.output_root, sample_set_name)
    run_dir, manifest = run_regression(
        args.sample_dir,
        args.output_root,
        args.sample_set,
        compare_to=compare_to,
    )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "sample_set": manifest["sample_set"],
                "totals": manifest["totals"],
                "comparison_available": manifest["comparison"]["available"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
