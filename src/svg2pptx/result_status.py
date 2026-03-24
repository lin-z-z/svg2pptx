"""Stable page-level status and issue-code helpers for structured export results."""

from __future__ import annotations


STATUS_SUCCESS = "success"
STATUS_WARNING = "warning"
STATUS_DEGRADED = "degraded"
STATUS_FAILURE = "failure"

FALLBACK_NONE = "NONE"
FALLBACK_KEEP_WARNING = "KEEP_OUTPUT_WITH_WARNING"
FALLBACK_KEEP_DEGRADED = "KEEP_OUTPUT_WITH_DEGRADATION"
FALLBACK_SKIP_PAGE = "SKIP_PAGE"


def _append_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def _map_render_warning_codes(render_warnings: list[dict]) -> list[str]:
    mapping = {
        "shape-count-overflow": "RENDER_SHAPE_LIMIT_EXCEEDED",
        "freeform-points-per-shape-overflow": "RENDER_FREEFORM_POINTS_PER_SHAPE_EXCEEDED",
        "freeform-points-per-page-overflow": "RENDER_FREEFORM_POINTS_PER_PAGE_EXCEEDED",
    }
    codes: list[str] = []
    for warning in render_warnings:
        code = mapping.get(warning.get("code", ""), "RENDER_WARNING")
        _append_unique(codes, code)
    return codes


def _map_unsupported_style_codes(unsupported_styles: list[dict]) -> list[str]:
    codes: list[str] = []
    for item in unsupported_styles:
        property_name = item.get("property", "")
        reason = item.get("reason", "")
        if property_name == "filter":
            _append_unique(codes, "FILTER_UNSUPPORTED")
        elif reason == "unresolved-url-reference":
            _append_unique(codes, "STYLE_UNRESOLVED_REFERENCE")
        else:
            _append_unique(codes, "STYLE_UNSUPPORTED")
    return codes


def _map_filter_codes(filter_results: list[dict]) -> list[str]:
    codes: list[str] = []
    for item in filter_results:
        support_level = item.get("support_level", "")
        if support_level == "approximate":
            _append_unique(codes, "FILTER_APPROXIMATION")
        elif support_level == "controlled_degradation":
            _append_unique(codes, "FILTER_CONTROLLED_DEGRADATION")
        elif support_level == "unsupported":
            _append_unique(codes, "FILTER_UNSUPPORTED")
    return codes


def _map_risk_tag_codes(risk_tags: list[str]) -> list[str]:
    mapping = {
        "text_dense": "TEXT_COMPLEXITY",
        "tspan_complex": "TEXT_TSPAN_COMPLEXITY",
        "curve_path": "GEOMETRY_CURVE_COMPLEXITY",
        "transform_heavy": "GEOMETRY_TRANSFORM_COMPLEXITY",
        "filter": "FILTER_COMPLEXITY",
        "gradient": "STYLE_GRADIENT_COMPLEXITY",
        "opacity_stack": "STYLE_OPACITY_STACK",
    }
    codes: list[str] = []
    for tag in risk_tags:
        mapped = mapping.get(tag)
        if mapped:
            _append_unique(codes, mapped)
    return codes


def classify_page_result(
    *,
    error: str = "",
    render_warnings: list[dict] | None = None,
    unsupported_styles: list[dict] | None = None,
    filter_results: list[dict] | None = None,
    risk_tags: list[str] | None = None,
) -> dict:
    render_warnings = render_warnings or []
    unsupported_styles = unsupported_styles or []
    filter_results = filter_results or []
    risk_tags = risk_tags or []

    issue_codes: list[str] = []
    signal_codes = _map_risk_tag_codes(risk_tags)
    for code in _map_render_warning_codes(render_warnings):
        _append_unique(issue_codes, code)
    for code in _map_unsupported_style_codes(unsupported_styles):
        _append_unique(issue_codes, code)
    for code in _map_filter_codes(filter_results):
        _append_unique(issue_codes, code)

    if error:
        status = STATUS_FAILURE
        status_code = "RUNTIME_EXCEPTION"
        fallback_code = FALLBACK_SKIP_PAGE
        _append_unique(issue_codes, status_code)
    elif render_warnings:
        status = STATUS_WARNING
        status_code = "RENDER_WARNING"
        fallback_code = FALLBACK_KEEP_WARNING
    elif issue_codes:
        status = STATUS_DEGRADED
        status_code = issue_codes[0]
        fallback_code = FALLBACK_KEEP_DEGRADED
    else:
        status = STATUS_SUCCESS
        status_code = "OK"
        fallback_code = FALLBACK_NONE

    return {
        "page_status": status,
        "status_code": status_code,
        "fallback_code": fallback_code,
        "issue_codes": issue_codes,
        "signal_codes": signal_codes,
    }


def summarize_page_statuses(results: list[dict]) -> dict:
    status_counts = {
        STATUS_SUCCESS: 0,
        STATUS_WARNING: 0,
        STATUS_DEGRADED: 0,
        STATUS_FAILURE: 0,
    }
    issue_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.get("page_status", STATUS_SUCCESS)] += 1
        for code in result.get("issue_codes", []):
            issue_counts[code] = issue_counts.get(code, 0) + 1
    return {
        "page_status_counts": status_counts,
        "issue_code_counts": dict(sorted(issue_counts.items())),
    }
