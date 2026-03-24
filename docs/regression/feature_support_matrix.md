# svg2pptx Fork Feature Support Matrix

本矩阵只描述当前 fork 在 OceanPPT 固定样本上的真实状态。
判定优先级：

1. `tests/*`
2. `artifacts/regression_runs/*/run.json`
3. `reports/regression_report.md`
4. 本文档

## 支持矩阵

| 能力 | 当前状态 | 证据 | 备注 |
| --- | --- | --- | --- |
| 基础几何与坐标映射 | 稳定 | `SVG-050` `SVG-060`；`tests/test_geometry.py` | 已统一 geometry 投影和 viewBox 映射 |
| `rect/circle/ellipse/line` 原生写入 | 稳定 | `tests/test_converter.py` | 直接写成 PPT 原生 shape |
| `polygon/polyline` freeform 写入 | 稳定 | `scripts/diag_svg2pptx.py` + `full_15` 回归 | 已纳入点数统计和 render guard |
| `path` 曲线写入 | 近似支持 | `src/svg2pptx/config.py` `curve_tolerance`；`SVG-150` 未完成 | 仍依赖曲线离散，精度还在继续优化 |
| group flatten 模式 | 稳定 | `full_15` 15/15 成功 | 当前默认推荐路径 |
| preserve group 模式 | 实验中 | `SVG-140` 未闭环 | z-order / 保序仍需真实复现后修复 |
| 文本框与 run 写入 | 部分稳定 | `SVG-070` `SVG-080` `SVG-090` | 自动化稳定，复杂页面仍需人工视觉复核 |
| 线性渐变 | 部分支持 | `full_15_week7_pipeline_v2` `linear_applied = 21` | 当前样本主流路径已接通 |
| 径向渐变 | 未验证 | `radial_applied = 0` | 当前固定样本没有有效覆盖 |
| 常见阴影 / glow filter | 近似支持 | `SVG-130` | 使用 PPT `outer shadow` / `glow` 近似 |
| CSS `drop-shadow(...)` token | 不支持 | `unsupported_styles_summary` | 会进入 diagnostics，不会静默丢失 |
| shape 膨胀与点数告警 | 稳定 | `SVG-160` | 默认阈值基于 `full_15` 峰值留余量 |
| 15 页全量回归 | 稳定 | `SVG-170` | 已有问题分级、关键指标、产物路径和 compare-last |

## 当前高频已知限制

- `fill=url(#grid)` / `url(#gridPattern)` 仍会落入 unresolved reference
- filter 只覆盖样本内高频链路，不追求任意 SVG filter 完整实现
- 文本和复杂曲线依然是后续提升主线

## 推荐使用方式

- 默认使用 `flatten_groups=True`
- 默认先跑 `full_15` 回归，再看是否值得推进新的渲染修复
- 新能力声明必须同时补：
  - 自动化测试
  - `run.json` 结构化证据
  - 本矩阵或相关文档
