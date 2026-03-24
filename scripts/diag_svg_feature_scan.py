"""Scan SVG fixtures and emit page-level feature diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

URL_REF_RE = re.compile(r"url\(#([^)]+)\)")
CURVE_COMMAND_RE = re.compile(r"[CSQTAcsqta]")
URL_ATTRS = ("fill", "stroke", "filter", "clip-path", "mask")
OPACITY_ATTRS = ("opacity", "fill-opacity", "stroke-opacity")
FILTER_STRATEGY_VERSION = "2026-03-24.filter-matrix-v1"


def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1].lower()


def _extract_url_refs(value: str | None) -> list[str]:
    if not value:
        return []
    return URL_REF_RE.findall(value)


def _collect_defined_ids(root: ET.Element) -> set[str]:
    return {
        element_id
        for element in root.iter()
        if (element_id := element.get("id"))
    }


def _page_title(text_samples: list[str], fallback: str) -> str:
    for text in text_samples:
        cleaned = text.strip()
        if cleaned:
            return cleaned
    return fallback


def _classify_filter_primitives(primitives: list[str]) -> dict:
    """Map a filter primitive chain to the current support/degradation contract."""
    normalized = tuple(primitives)
    if normalized == ("fedropshadow",):
        return {
            "support_level": "approximate",
            "current_action": "controlled_degradation",
            "degradation_note": "单一 feDropShadow 已进入近似支持矩阵，当前导出先保留主体并记录，后续由 SVG-130 落视觉等价。",
        }
    if normalized == (
        "fegaussianblur",
        "feoffset",
        "fecomponenttransfer",
        "femerge",
    ):
        return {
            "support_level": "approximate",
            "current_action": "controlled_degradation",
            "degradation_note": "典型阴影链可近似映射为 PowerPoint 阴影，当前导出先记录降级，后续由 SVG-130 实装。",
        }
    if normalized == ("fegaussianblur", "fecomposite"):
        return {
            "support_level": "controlled_degradation",
            "current_action": "record_only",
            "degradation_note": "模糊加 composite 更接近 glow，当前只输出降级记录，不静默忽略。",
        }
    if not normalized:
        return {
            "support_level": "unsupported",
            "current_action": "record_only",
            "degradation_note": "filter 定义为空或未识别子节点，当前无法映射。",
        }
    return {
        "support_level": "unsupported",
        "current_action": "record_only",
        "degradation_note": "filter primitive 链未进入当前支持矩阵，当前保留主体图形并记录。",
    }


def _collect_filter_definitions(root: ET.Element) -> dict[str, dict]:
    """Collect filter definitions and classify each chain once per page."""
    filter_defs: dict[str, dict] = {}
    for element in root.iter():
        if _strip_ns(element.tag) != "filter":
            continue
        filter_id = element.get("id")
        if not filter_id:
            continue
        primitives = [
            _strip_ns(child.tag)
            for child in element
            if _strip_ns(child.tag).startswith("fe")
        ]
        filter_defs[filter_id] = {
            "filter_id": filter_id,
            "primitive_chain": primitives,
            **_classify_filter_primitives(primitives),
        }
    return filter_defs


def _collect_filter_usage(root: ET.Element, filter_defs: dict[str, dict]) -> list[dict]:
    """Return one summarized record per filter reference used on the page."""
    usage_counter: Counter[str] = Counter()
    tag_counter: dict[str, Counter[str]] = {}

    for element in root.iter():
        filter_attr = element.get("filter")
        if not filter_attr:
            continue
        refs = _extract_url_refs(filter_attr)
        if not refs:
            continue
        tag = _strip_ns(element.tag)
        tag_counter.setdefault(tag, Counter()).update(refs)
        usage_counter.update(refs)

    results: list[dict] = []
    for filter_id, count in sorted(usage_counter.items()):
        if filter_id in filter_defs:
            entry = dict(filter_defs[filter_id])
        else:
            entry = {
                "filter_id": filter_id,
                "primitive_chain": [],
                "support_level": "unsupported",
                "current_action": "record_only",
                "degradation_note": "filter 引用未在 defs 中找到，导出时只能忽略并记录。",
            }
        entry["applied_count"] = count
        entry["applied_on"] = sorted(
            tag for tag, counter in tag_counter.items() if counter.get(filter_id)
        )
        results.append(entry)
    return results


def scan_svg(svg_path: Path) -> dict:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    counts: Counter[str] = Counter()
    transform_nodes = 0
    opacity_nodes = 0
    url_refs: list[str] = []
    curve_paths = 0
    text_samples: list[str] = []

    for element in root.iter():
        tag = _strip_ns(element.tag)
        counts[tag] += 1

        if element.get("transform"):
            transform_nodes += 1

        if any(element.get(attr) for attr in OPACITY_ATTRS):
            opacity_nodes += 1

        for attr in URL_ATTRS:
            url_refs.extend(_extract_url_refs(element.get(attr)))

        if tag == "path" and CURVE_COMMAND_RE.search(element.get("d", "")):
            curve_paths += 1

        if tag == "text":
            text_value = "".join(element.itertext()).strip()
            if text_value:
                text_samples.append(text_value)

    defined_ids = _collect_defined_ids(root)
    filter_defs = _collect_filter_definitions(root)
    filter_usage = _collect_filter_usage(root, filter_defs)
    unresolved_refs = sorted({ref for ref in url_refs if ref not in defined_ids})

    metrics = {
        "transform_nodes": transform_nodes,
        "gradient_defs": counts["lineargradient"] + counts["radialgradient"],
        "filter_defs": counts["filter"],
        "text_nodes": counts["text"],
        "tspan_nodes": counts["tspan"],
        "opacity_nodes": opacity_nodes,
        "curve_paths": curve_paths,
        "url_refs": len(url_refs),
        "unresolved_refs": len(unresolved_refs),
    }

    risk_tags: list[str] = []
    if metrics["transform_nodes"] >= 8:
        risk_tags.append("transform_heavy")
    if metrics["gradient_defs"] > 0:
        risk_tags.append("gradient")
    if metrics["filter_defs"] > 0 or any("filter" in ref.lower() for ref in url_refs):
        risk_tags.append("filter")
    if metrics["text_nodes"] >= 16:
        risk_tags.append("text_dense")
    if metrics["tspan_nodes"] >= 3:
        risk_tags.append("tspan_complex")
    if metrics["opacity_nodes"] >= 6:
        risk_tags.append("opacity_stack")
    if metrics["curve_paths"] > 0:
        risk_tags.append("curve_path")
    if unresolved_refs:
        risk_tags.append("unresolved_ref")
    if root.get("viewBox") is None:
        risk_tags.append("missing_viewbox")

    return {
        "page_id": svg_path.stem,
        "file_name": svg_path.name,
        "title_hint": _page_title(text_samples, svg_path.stem),
        "metrics": metrics,
        "risk_tags": risk_tags,
        "unresolved_refs": unresolved_refs,
        "top_text_samples": text_samples[:6],
        "filters": filter_usage,
        "filter_strategy_version": FILTER_STRATEGY_VERSION,
    }


def scan_svg_directory(input_dir: Path, output_dir: Path | None = None, sample_set: str | None = None) -> dict:
    svg_files = sorted(input_dir.glob("*.svg"))
    if not svg_files:
        raise ValueError(f"No SVG files found in {input_dir}")

    page_reports = [scan_svg(path) for path in svg_files]
    totals = Counter()
    risk_distribution = Counter()
    unresolved_pages: list[str] = []
    filter_support = Counter()
    filter_actions = Counter()
    filter_primitives = Counter()
    pages_with_filters: list[str] = []

    for report in page_reports:
        totals.update(report["metrics"])
        risk_distribution.update(report["risk_tags"])
        if report["unresolved_refs"]:
            unresolved_pages.append(report["page_id"])
        if report["filters"]:
            pages_with_filters.append(report["page_id"])
        for filter_item in report["filters"]:
            filter_support.update([filter_item["support_level"]])
            filter_actions.update([filter_item["current_action"]])
            filter_primitives.update(filter_item["primitive_chain"])

    summary = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_set": sample_set or input_dir.name,
        "input_dir": str(input_dir),
        "page_count": len(page_reports),
        "totals": dict(totals),
        "risk_distribution": dict(risk_distribution),
        "pages_with_unresolved_refs": unresolved_pages,
        "filter_support_summary": {
            "strategy_version": FILTER_STRATEGY_VERSION,
            "pages_with_filters": pages_with_filters,
            "support_levels": dict(filter_support),
            "current_actions": dict(filter_actions),
            "primitive_usage": dict(filter_primitives),
        },
        "pages": page_reports,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        pages_dir = output_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        for report in page_reports:
            (pages_dir / f"{report['page_id']}.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan SVG fixtures and emit structured feature diagnostics.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing SVG pages.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for summary.json and page reports.",
    )
    parser.add_argument(
        "--sample-set",
        type=str,
        default=None,
        help="Logical sample set name written into summary.json.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    summary = scan_svg_directory(args.input_dir, args.output_dir, args.sample_set)
    print(
        json.dumps(
            {
                "sample_set": summary["sample_set"],
                "page_count": summary["page_count"],
                "totals": summary["totals"],
                "risk_distribution": summary["risk_distribution"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
