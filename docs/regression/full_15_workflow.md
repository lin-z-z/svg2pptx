# full_15 Regression Workflow

这份说明对应当前 fork 的标准 15 页全量回归流程。

## 1. 环境准备

```powershell
conda run -n svg2pptx python -m pip install -e .
conda run -n svg2pptx python -m pip install pytest
```

## 2. 先跑最相关自动化测试

```powershell
conda run -n svg2pptx python -m pytest tests\test_converter.py tests\test_diagnostics.py -q
```

如果当前改动碰到 geometry / curve 近似，再加：

```powershell
conda run -n svg2pptx python -m pytest tests\test_geometry.py -q
```

## 3. 第一次跑 full_15

```powershell
conda run -n svg2pptx python scripts\diag_svg2pptx.py `
  --sample-set full_15_week7_pipeline_v2 `
  --output-root artifacts\regression_runs
```

第一次运行的目标：

- 确认 `page_count = 15`
- 确认 `success_count = 15`
- 生成完整产物目录

## 4. 第二次跑并和上一轮对比

```powershell
conda run -n svg2pptx python scripts\diag_svg2pptx.py `
  --sample-set full_15_week7_pipeline_v2 `
  --output-root artifacts\regression_runs `
  --compare-last
```

第二次运行后需要确认：

- CLI 输出 `comparison_available = true`
- `run.json` 包含 `comparison`
- 报告里出现 `与上次回归对比`

## 5. 必查产物

必须检查这些文件：

- `run.json`
- `reports/regression_report.md`
- `reports/manual_score.csv`
- `reports/svg_scan/summary.json`
- `pptx/slide_001.pptx ... slide_015.pptx`

## 6. run.json 必看字段

至少核对：

- `totals`
- `problem_summary`
- `key_metrics`
- `render_protection_summary`
- `unsupported_styles_summary`
- `comparison`

## 7. 人工评分建议

自动化跑完后，再用 `reports/manual_score.csv` 做人工补充：

- 布局
- 文本
- 样式
- 层级
- 可编辑性

如果改动涉及文本、filter、group 或 path：

- 至少抽 3 页高风险页做 PowerPoint 人工复核
- 不要只看 `success_count`

## 8. 当前已验证的基线事实

以 `2026-03-24_04-26-47_full_15_week7_pipeline_v2` 为例：

- `15/15` 成功
- `problem_counts = high 0 / medium 0 / low 14 / clean 1`
- `render_warning_count = 0`
- `max_shape_count = 57`
- `max_freeform_points = 61`
- `unsupported_style_item_count = 9`

## 9. 常见误区

- `comparison_available = false` 不一定是 bug，第一次跑本来就没有上一轮
- `low` 问题页不等于失败页，通常表示当前样本里仍存在已知限制或近似实现
- 不要把 `risk_tags` 当成真实问题分级，它们是扫描风险提示，不是导出失败
