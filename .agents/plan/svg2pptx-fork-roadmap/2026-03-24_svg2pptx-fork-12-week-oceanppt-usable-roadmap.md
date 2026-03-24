# svg2pptx Fork 12 周可接入首版路线

> 创建时间：2026-03-24  
> 目标版本：**第一版可在 OceanPPT 侧以实验开关方式接入使用**  
> 样本基线：`artifacts/proj_716f3504142f/job_1d95c6459b55/svg_pages/slide_001.svg ~ slide_015.svg`  
> 特征扫描：`artifacts/debug/svg_feature_scan/2026-03-24_01-35-07/summary.json`  
> 关键约束：**不降低 SVG 视觉标准，不为了导出而弱化 OceanPPT 现有 SVG 表现**

---

## 1. 这份路线与 8 周版的区别

8 周版解决的是：

1. 把 `svg2pptx` 从早期库推进成 OceanPPT 专用 fork。
2. 建立基础回归、文本、几何、样式、滤镜能力。
3. 做出“有明确上限、可继续迭代”的研发版。

12 周版新增的目标是：

1. 让 fork **能在 OceanPPT 里挂成实验开关**。
2. 让第一版不只是“能导出”，而是“**能给你这里试用**”。
3. 给出真实的接入、回退、失败降级和验收方案。

一句话：

**8 周是研发版，12 周才是更现实的“可接入首版”。**

---

## 2. 现实工期判断

### 2.1 单人

如果只有 1 个人做，这条线更接近：

- 12 到 16 周：做出能接入 OceanPPT 的首版
- 16 周以上：才可能认真挑战 `SVGEdit` 兜底路线

### 2.2 双人

如果有 2 个强工程师：

- 10 到 12 周：有机会做出首版可接入
- 前提是工具链、回归样本、代码评审节奏都跟上

### 2.3 三到四人

如果你愿意加人，我建议至少按这 4 条 lane 并行：

1. `geometry/path` 线
2. `text/layout` 线
3. `styles/filter` 线
4. `tooling/integration` 线

这种配置下：

- 8 周：能出“比较像样的 fork 研发版”
- 10 到 12 周：更有机会做出“能在 OceanPPT 这边试用的首版”

---

## 3. 首版交付定义

这里的“可接入首版”不是指默认替换当前方案，而是指：

1. OceanPPT 增加一个实验导出后端开关，例如：
   - `export_backend=svg2pptx_fork`
   - `export_backend=powerpoint_svgedit`
   - `export_backend=pptxgenjs_svg_embed`

2. `svg2pptx_fork` 满足以下最低标准：
   - 15 页样本可稳定导出
   - 80% 页面达到“可交付预览”
   - 文本可编辑，不大面积丢失
   - 主要卡片、容器、标题、装饰线不严重错位
   - 导出失败时有结构化错误和回退建议

3. OceanPPT 可以在实验环境中真实调用它，完成：
   - 产物生成
   - 元数据记录
   - 导出状态显示
   - 失败回退

---

## 4. 分阶段目标

```text
Week 1-4   基础能力建设
Week 5-8   关键视觉能力与 15 页稳定性
Week 9-10  OceanPPT 接入与真实项目试用
Week 11-12 首版收口、失败治理、灰度准备
```

---

## 5. Week 1-8：沿用研发主线

Week 1-8 的研发主线，沿用 8 周版的核心范围：

1. Week 1：基线、样本、特征扫描、评分模板
2. Week 2：`transform` 与坐标系统
3. Week 3：文本与 `tspan`
4. Week 4：基础样式与渐变
5. Week 5：滤镜与受控降级
6. Week 6：group、z-order、path/freeform
7. Week 7：15 页全量回归与性能治理
8. Week 8：研发版 fork 文档、支持矩阵、Go/No-Go

这部分细节继续参考：

- `plan/svg2pptx-fork-roadmap/2026-03-24_svg2pptx-fork-8-week-roadmap.md`

---

## 6. Week 9：OceanPPT 接入层与实验开关

### 目标

把 fork 从“独立仓库里能跑”的研发版，推进成“能被 OceanPPT 调起来”的实验导出后端。

### 工作项

1. 在 OceanPPT 侧补导出后端抽象：
   - `pptxgenjs_svg_embed`
   - `powerpoint_svgedit`
   - `svg2pptx_fork`

2. 定义统一导出接口：
   - 输入：SVG 页面目录、项目元数据、导出配置
   - 输出：PPTX 路径、诊断报告、页面级状态摘要

3. 建实验开关：
   - `.env` 或项目配置切换导出后端
   - UI 或 API 可感知当前后端类型

4. 为 `svg2pptx_fork` 补包装层：
   - CLI
   - Python API
   - 结构化 JSON 报告

### 交付物

1. `oceanppt/export_backends/svg2pptx_fork_adapter.py`
2. `docs/oceanppt-integration-v1.md`
3. `artifacts/integration-smoke/`

### 验收标准

1. OceanPPT 能用实验开关触发 `svg2pptx_fork`。
2. 导出结果与错误都能被 OceanPPT 消费。
3. 切换后端不会破坏现有 `pptxgenjs` 与 `SVGEdit` 路线。

---

## 7. Week 10：真实项目试用与问题归因

### 目标

不要只拿 15 页固定样本自嗨，要拿真实 OceanPPT 项目做首轮试用。

### 工作项

1. 选 3 到 5 个真实项目做试用：
   - 不同页面数
   - 不同视觉密度
   - 不同文本复杂度

2. 记录每个项目的：
   - 成功率
   - 页面问题分类
   - 文本问题
   - 样式问题
   - 性能问题

3. 形成“固定样本 vs 真实项目”对比视图

4. 把高频问题重新映射回：
   - geometry
   - text
   - styles/filter
   - integration

### 交付物

1. `docs/trial-project-report-week10.md`
2. `artifacts/trial-projects/`
3. 高优先级缺陷 backlog

### 验收标准

1. 至少 3 个真实项目完成试用导出。
2. 每个项目的问题都能落到明确分类。
3. 不再只依赖 15 页样本判断“是否可用”。

---

## 8. Week 11：失败治理、降级与回退

### 目标

把“导出失败/局部页面效果差”的问题从黑盒事故，变成受控系统行为。

### 工作项

1. 增加页面级失败标记：
   - 成功
   - 警告
   - 受控降级
   - 失败

2. 增加失败原因分类：
   - text layout unsupported
   - filter unsupported
   - geometry overflow
   - shape count explosion
   - runtime exception

3. 增加回退策略：
   - 整 deck 回退到 `pptxgenjs_svg_embed`
   - 单项目建议改用 `SVGEdit`
   - 仅实验环境允许继续下载降级产物

4. OceanPPT 侧展示导出结果说明

### 交付物

1. `docs/failure-modes-and-fallbacks.md`
2. 结构化失败码与回退码表
3. OceanPPT 实验导出错误提示草案

### 验收标准

1. 首版接入后，失败不再是无提示崩溃。
2. 用户可以知道当前产物是正常、降级还是建议回退。
3. 回退路径真实可用。

---

## 9. Week 12：首版验收与灰度准备

### 目标

形成一个你这里能实际试用的首版，而不是继续停留在研发内部版本。

### 工作项

1. 形成首版验收包：
   - 15 页样本结果
   - 真实项目试用结果
   - 性能与失败报告
   - 已知限制清单

2. 形成灰度口径：
   - 只在实验开关下使用
   - 哪类项目建议开启
   - 哪类项目仍建议走 `SVGEdit`

3. 形成接入结论：
   - 可试用
   - 可小范围灰度
   - 暂不建议默认

4. 形成后续 4~8 周 backlog：
   - 必修项
   - 体验优化项
   - 是否继续挑战替代 `SVGEdit`

### 交付物

1. `docs/release-readiness-week12.md`
2. `docs/oceanppt-pilot-rollout.md`
3. `docs/post-week12-backlog.md`

### 验收标准

1. 你可以在 OceanPPT 这里真实切换到 `svg2pptx_fork` 做试用。
2. 有明确灰度策略和回退策略。
3. 有明确定义的已知限制，而不是“看起来能用”。

---

## 10. 推荐团队配置

### 最低配置：2 人

1. A：`geometry/path/group`
2. B：`text/style/filter/tooling`

风险：

- 集成与回归会成为瓶颈
- 12 周会很紧

### 推荐配置：3 人

1. A：`geometry/path/group`
2. B：`text/layout`
3. C：`styles/filter + tooling/integration`

这时 12 周做出可接入首版是有现实可能的。

### 更优配置：4 人

1. A：`geometry/path`
2. B：`text/layout`
3. C：`styles/filter`
4. D：`tooling/regression/integration`

这是我最推荐的配置。  
如果你真想要“第一版就能给 OceanPPT 这边使用”，这是比较稳的编制。

---

## 11. 关键里程碑

| 时间点 | 必须回答的问题 |
| --- | --- |
| Week 3 | 文本是否已经从“不可用”进入“基本可读可编” |
| Week 5 | 滤镜是否有受控等价策略，否则是否接受首版上限 |
| Week 7 | 15 页全量稳定性是否足以继续投资 |
| Week 8 | 研发版是否值得进入接入阶段 |
| Week 10 | 真实项目试用是否证明它不只是样本内有效 |
| Week 12 | 是否能在 OceanPPT 这里以实验开关方式真实使用 |

### 11.1 2026-03-24 Week 7 Gate Update

当前结论：**No-Go**

原因：

1. `15/15` 自动化导出成功不等于视觉可接入
2. `slide_001`、`slide_002` 这类页面在 PowerPoint 人工复核里仍有明显文本布局和背景失真
3. `slide_005` 暴露了 `pattern/url(#...)` 失效会导致语义级背景错误

因此：

- Week 8 不应把“进入 OceanPPT 接入阶段”当作默认继续项
- Week 8 应先补视觉保真度修复与再次 Go/No-Go 评审
- Week 9 之后的 adapter / 前端开关 / 回退策略应视为被当前 Gate 阻塞

对应评审记录见 `docs/regression/week7_go_no_go_review_2026-03-24.md`

---

## 12. 最终口径

### 12.1 我给你的明确判断

如果你的目标是：

> 第一版出来就能给 OceanPPT 这里使用

那我建议你不要再把工期口径说成 8 周，而是：

**按 12 周做首版接入计划，8 周只看作研发能力建设阶段。**

### 12.2 成功定义

Week 12 成功不代表：

- 默认替代 `SVGEdit`
- 全量项目都比 `SVGEdit` 好

Week 12 成功代表：

1. OceanPPT 已可切实验开关试用
2. 有结构化回归和真实项目试用证据
3. 有失败降级和回退方案
4. 有明确已知限制

### 12.3 一句话结论

**如果你想让第一版就能在 OceanPPT 这里用，建议把路线升级成 12 周，并按 3~4 人并行配置推进。**
