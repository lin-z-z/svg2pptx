# OceanPPT SVG 固定样本

这里冻结的是 `svg2pptx` fork 的 Week 1 固定输入合同。

## 目录

- `full_15/`
  - 15 页全量样本，直接来自 `.agents/plan/svg2pptx-fork-roadmap/svg_pages/`
- `baseline_5/`
  - 5 页代表性样本，用于快速回归和人工评分

## baseline_5 选页

- `slide_001.svg`
  - 封面页，包含标题、渐变和基础变换
- `slide_002.svg`
  - 目录/多栏页，文本密度高，包含 filter url 引用
- `slide_005.svg`
  - 卡片和结构化布局页，适合观察容器与层级
- `slide_006.svg`
  - 复杂文本页，包含长段正文和多个 `tspan`
- `slide_008.svg`
  - 渐变 + filter 场景页，用于观察高风险视觉特征

## 来源

- 复制源：`.agents/plan/svg2pptx-fork-roadmap/svg_pages/slide_001.svg ~ slide_015.svg`
- 冻结时间：`2026-03-24`
- 约束：
  - 不修改 SVG 内容，只复制并固定目录合同
  - 新增或替换样本时必须同步更新 `manifest.json`
