# svg2pptx Fork for OceanPPT

这是一个面向 OceanPPT 固定样本的 `svg2pptx` fork。
当前目标不是“完整支持任意 SVG”，而是围绕
`tests/fixtures/oceanppt/{baseline_5,full_15}` 形成一条可复跑、
可诊断、可逐步提升的 PowerPoint 可编辑导出链路。

## 当前状态

- 固定样本已经冻结在仓库内，不依赖 OceanPPT 外部路径。
- `full_15` 回归入口已经标准化，可输出 `run.json`、PPTX、扫描结果、
  手工评分模板和 Markdown 报告。
- 回归报告现在包含问题分级、关键指标、产物路径，以及
  `--compare-last` 的上次结果对比。

2026-03-24 的最新 `full_15_week7_pipeline_v2` 结果：

- `15/15` 页面导出成功
- `problem_counts = high 0 / medium 0 / low 14 / clean 1`
- `render_warning_count = 0`
- `max_shape_count = 57`
- `max_freeform_points = 61`
- `max_points_single_shape = 41`

## 环境准备

推荐直接使用项目约定环境：

```powershell
conda run -n svg2pptx python -m pip install -e .
```

如果当前环境还没有测试依赖：

```powershell
conda run -n svg2pptx python -m pip install pytest
```

## 单文件转换

当前最稳定的集成入口仍然是 Python API：

```python
from svg2pptx import Config, svg_to_pptx

config = Config(
    curve_tolerance=1.0,
    preserve_groups=False,
    flatten_groups=True,
)

svg_to_pptx("input.svg", "output.pptx", config=config)
```

说明：

- `curve_tolerance` 越小，曲线采样越细，点数也会更多。
- `preserve_groups=True` 仍属于实验路径，`SVG-140` 还没有闭环。
- path/freeform 曲线精度仍在继续优化，见 `SVG-150`。

## 目录批量导出与结构化结果

如果你要把一批 SVG 页面导成 PPTX，并拿到结构化结果，当前推荐用
`convert_svg_inputs()`：

```python
from svg2pptx import convert_svg_inputs

report = convert_svg_inputs(
    "tests/fixtures/oceanppt/baseline_5",
    "artifacts/api_batch_smoke",
)

print(report["status"])
print(report["totals"])
```

CLI 也复用了同一份合同：

```powershell
conda run -n svg2pptx python -m svg2pptx `
  tests\fixtures\oceanppt\baseline_5 `
  artifacts\cli_batch_smoke `
  --report-json artifacts\cli_batch_smoke\report.json `
  --json
```

新的结构化结果会包含：

- `status`
- `input` / `output`
- `config`
- `totals`
- `page_status_counts`
- `issue_code_counts`
- `results[*].gradient_stats`
- `results[*].render_metrics`
- `results[*].render_warnings`
- `results[*].unsupported_styles`
- `results[*].page_status`
- `results[*].status_code`
- `results[*].fallback_code`
- `results[*].issue_codes`

## 标准回归入口

推荐把下面这条命令当作当前 fork 的标准入口：

```powershell
conda run -n svg2pptx python scripts\diag_svg2pptx.py `
  --sample-set full_15_week7_pipeline_v2 `
  --output-root artifacts\regression_runs `
  --compare-last
```

说明：

- 默认样本目录就是 `tests/fixtures/oceanppt/full_15`
- 第一次运行可以去掉 `--compare-last`
- 第二次开始可打开 `--compare-last`，自动对比同 `sample_set` 的上一轮

典型产物目录结构：

```text
artifacts/regression_runs/<timestamp>_<sample_set>/
├── run.json
├── pptx/
│   └── slide_001.pptx ... slide_015.pptx
└── reports/
    ├── manual_score.csv
    ├── regression_report.md
    └── svg_scan/
        ├── summary.json
        └── pages/*.json
```

## 文档入口

- 支持矩阵：
  `docs/regression/feature_support_matrix.md`
- 15 页回归操作说明：
  `docs/regression/full_15_workflow.md`
- 报告模板：
  `docs/regression/report_template.md`

## 当前已知限制

- 组结构保序和 z-order 保持还未闭环，见 `SVG-140`
- path/freeform 曲线几何精度还在继续收敛，见 `SVG-150`
- 滤镜只覆盖当前样本中高频的阴影/发光近似；CSS `drop-shadow(...)`
  token 仍会进入 unsupported diagnostics
- 文本框宽高仍带启发式，复杂页面需要 PowerPoint 人工视觉复核

## 推荐验收顺序

1. 先跑自动化测试：

```powershell
conda run -n svg2pptx python -m pytest tests\test_converter.py tests\test_diagnostics.py -q
```

2. 再跑一次 `full_15` 标准回归
3. 打开 `run.json` 看：
   - `totals`
   - `problem_summary`
   - `key_metrics`
   - `render_protection_summary`
   - `comparison`
4. 最后按 `reports/manual_score.csv` 做抽样人工评分

## 不要误解的边界

- 这个 fork 现在是“样本驱动优化”，不是通用 SVG 渲染引擎
- `README` 里的能力声明应该以 `run.json + tests + docs/regression/*`
  为准，不要再回退去看原始上游 README 的泛化表述
- OceanPPT 接入、adapter、前端开关和真实项目试用都还在后续 CSV issue
  里，当前仓库不会直接修改 OceanPPT 代码
