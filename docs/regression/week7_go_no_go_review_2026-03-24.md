# Week 7 Go/No-Go 评审记录

日期：2026-03-24

对应 issue：`SVG-190`

## 1. 评审范围

本次评审只判断一件事：

- 当前 `svg2pptx` fork 是否已经达到“值得进入 OceanPPT 接入阶段”的 Week 7 门槛

评审边界：

- 不修改 OceanPPT 仓库
- 自动化证据来自 15 页全量回归
- 人工证据来自 PowerPoint 可复核抽样，而不是只看终端日志

## 2. 证据来源

### 2.1 自动化回归

1. 直接目录批量导出：

```powershell
conda run -n svg2pptx python -m svg2pptx `
  .agents\plan\svg2pptx-fork-roadmap\svg_pages `
  artifacts\svg_pages_tryout `
  --report-json artifacts\svg_pages_tryout\report.json `
  --json
```

2. 结构化回归运行器：

```powershell
conda run -n svg2pptx python scripts\diag_svg2pptx.py `
  --sample-dir .agents\plan\svg2pptx-fork-roadmap\svg_pages `
  --output-root artifacts\regression_runs `
  --sample-set svg_pages_tryout
```

### 2.2 PowerPoint 人工复核

抽样页：

- `slide_001`：报告 `OK` 的封面页，检查“成功页是否真的视觉可用”
- `slide_002`：报告 `FILTER_APPROXIMATION` 的目录页，检查自动化 `low` 是否被低估
- `slide_004`：报告 `FILTER_UNSUPPORTED` 的图表页，检查滤镜降级是否仍可接受
- `slide_005`：报告 `STYLE_UNRESOLVED_REFERENCE` 的 pattern 背景页，检查 `url(#...)` 失效的真实后果

复核方法：

1. 用 PowerPoint COM 把生成的 `pptx` 导出成 `png`
2. 用 ImageMagick 把源 `svg` 栅格化成 `png`
3. 拼成并排对比图，人工核对布局、文本、样式、层级和可编辑性

对比图路径：

- `artifacts/visual_compare/slide_001_compare.png`
- `artifacts/visual_compare/slide_002_compare.png`
- `artifacts/visual_compare/slide_004_compare.png`
- `artifacts/visual_compare/slide_005_compare.png`

人工评分表：

- `docs/regression/week7_go_no_go_manual_score_2026-03-24.csv`

## 3. 自动化结论

`artifacts/svg_pages_tryout/report.json`：

- `15/15` 页面导出成功
- `page_status_counts = success 6 / degraded 9 / failure 0`
- `issue_code_counts = FILTER_UNSUPPORTED 3 / STYLE_UNRESOLVED_REFERENCE 6`

`artifacts/regression_runs/2026-03-24_07-53-27_svg_pages_tryout/run.json`：

- `page_status_counts = success 1 / degraded 14 / failure 0`
- `problem_counts = high 0 / medium 0 / low 14 / clean 1`
- `unsupported_style_item_count = 9`
- `render_warning_count = 0`
- `duration_ms_total = 1058.45`
- `slowest_page = slide_001 / 578.66 ms`

自动化层面的结论是：

- 当前 fork 没有“导不出来”的硬失败
- 但大量页面依然处于 `degraded`
- `high 0 / medium 0` 只能说明“没有被规则命中为严重问题”，不能直接推导成“视觉可接入”

## 4. 人工抽样结论

### 4.1 `slide_001`

- 报告是 `page_status=success` / `status_code=OK`
- 真实对比里，主标题明显放大、下沉，右上渐变圆和飞行器装饰也出现明显走样

结论：

- `success/OK` 不能作为 Week 7 放行依据
- 当前“成功页”依然可能存在显著文本布局和装饰几何误差

### 4.2 `slide_002`

- 自动化只给出 `low / filter-approximation`
- 真实对比里，整页蓝色背景被放大覆盖，目录页语义已经发生变化

结论：

- 当前问题分级低估了部分页面的视觉影响
- 目录类页面还存在明显的背景/布局失真

### 4.3 `slide_004`

- 报告为 `FILTER_UNSUPPORTED`
- 真实对比里，主结构和文案仍基本保持，属于“可读但降级”的情况

结论：

- 滤镜页并非全部不可用
- 但这类页面目前最多只能算“受控降级”，还不是稳定达标

### 4.4 `slide_005`

- 报告为 `STYLE_UNRESOLVED_REFERENCE`
- 真实对比里，`pattern id="grid"` 丢失后，左侧技术卡片被错误刷成整块蓝底，视觉语义被改写

结论：

- `url(#...)` / `pattern` 类引用目前仍会造成语义级错误
- 这不是轻微样式损失，而是会误导用户的版面错误

## 5. Week 7 决策

结论：**No-Go**

原因不是“导不进去”，而是：

1. 自动化 `success_count` 和 `problem_counts` 还不能代表真实视觉可用
2. 报告 `OK` 的页面依然存在明显文本布局和装饰几何失真
3. `pattern/url(#...)` 失效会引入大面积错误填充，属于语义级问题
4. 滤镜页虽有部分受控降级，但整体稳定性还不足以直接进入 OceanPPT 接入

## 6. 对 Week 8-12 的影响

本轮评审后的范围调整：

- **不要**把 Week 8 的主目标继续定义成“进入 OceanPPT 接入阶段”
- Week 8 应先补“视觉保真度修复 + 再次 Go/No-Go 复核”
- Week 9 之后的 OceanPPT adapter / 前端开关 / 回退策略，应视为被当前 No-Go 结论阻塞

当前建议优先级：

1. 先修“成功页仍失真”的文本布局与背景/变换问题
2. 再修 `pattern/url(#...)` 与常见 defs 引用
3. 最后再继续收口 filter 的受控降级

## 7. 解除 No-Go 的最低条件

再次评审前，至少满足：

1. 至少 3 页代表页完成 PowerPoint 人工复核，且 `overall_score >= 4`
2. 报告为 `success` 的页面不再出现主标题放大、背景覆盖或装饰几何明显走样
3. `pattern/url(#...)` 不再引入大面积错误填充
4. filter 页即使降级，也必须保持主要层级和视觉语义不变

## 8. 一句话结论

当前 fork 已具备“稳定导出 + 结构化诊断”的能力，  
但还没有达到“值得立即进入 OceanPPT 接入阶段”的视觉保真度门槛。
