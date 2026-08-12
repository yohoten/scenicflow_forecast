# Power BI 看板规划：九寨沟客流运营决策分析

> 目的：补上简历里"Power BI（了解）"的短板，交出一个**真实、可演示、体现标准 BI 能力**的作品。
> 思路：复用你最强的九寨沟数据，与 Streamlit 的"预测"定位互补——Power BI 侧主打"运营决策 + 交互下钻 + 同比环比"，证明你掌握**数据建模（星型模型）+ DAX 度量值 + 交互式分析**，这正是央国企 BI 岗筛选硬门槛。

---

## 一、数据源

用你已有的 1869 天日度数据，导出为 `jiuzhaigou_daily.csv`（字段建议）：

| 字段 | 类型 | 说明 |
|------|------|------|
| date | 日期 | 主键 |
| visitors | 整数 | 当日客流（事实） |
| temperature | 数值 | 当日气温 |
| weather | 文本 | 晴/雨/阴/雪 |
| is_holiday | 布尔 | 是否法定节假日 |
| holiday_name | 文本 | 节假日名称（无则空） |
| pred_visitors | 数值 | 模型 7 日预测值（可选，做预测对比页） |
| pred_lower / pred_upper | 数值 | 90% 置信区间上下界 |

> 若原始数据是宽表（40 维特征），看板只需上面这些"业务字段"，其余特征留给建模用，不要把 40 列全塞进看板。

---

## 二、数据模型（星型模型，体现 BI 专业度）

Power BI 里建关系，而不是堆一张大表：

```
fact_daily (事实表)           dim_date (日期维)          dim_holiday (节假日维)
- date (FK)  ─────────────►  - date (PK)               - holiday_name (PK)
- visitors                  - year                     - date (FK→dim_date)
- temperature               - month                    - type (法定/调休/小长假)
- weather                   - weekday
- is_holiday                - season (春/夏/秋/冬)
- pred_visitors             - is_weekend
- pred_lower
- pred_upper
```

要点：
- **事实表只放可累加的度量**（visitors、pred 等）和键值；
- **维度表放描述性字段**（年/月/季节/节假日类型），用于切片、下钻、同比环比；
- 在 Power BI "模型"视图里拉好关系，面试时能讲清"为什么用星型模型"——查询快、语义清晰、避免冗余。

---

## 三、页面规划（4 页）

**Page 1 · 总览 KPI**
- KPI 卡片：年度总客流、日均客流、年内峰值日及数值、当前承载力饱和度
- 年度客流趋势折线（可切片年份）
- 切片器：年份、季节、是否节假日

**Page 2 · 趋势与预测**
- 实际 vs 预测折线（近 30 天 + 未来 7 日），预测段用 90% 置信带（误差带视觉效果）
- 同比按钮（本年度 vs 上年度）

**Page 3 · 因素分析**
- 各节假日平均客流条形图（识别哪些节最旺）
- 月度季节性热力图 / 柱图（哪个月是旺季）
- Top 驱动因子（可放 SHAP Top5 条形，从建模结果导出静态表）

**Page 4 · 运营建议（预警表）**
- 表：未来 7 日 | 预测客流 | 饱和度 S | 预警状态 | 建议动作
- 条件格式：S>0.9 红色高亮
- 这是"业务闭环"的 BI 落地页，和你的 Streamlit 预测、运营策略文档形成统一故事

---

## 四、关键 DAX 度量值（必须会写、会被问）

```DAX
总客流 = SUM(fact_daily[visitors])

日均客流 = AVERAGE(fact_daily[visitors])

承载量 T = 41000          -- 改为你的核定值（参数化）

日饱和度 = DIVIDE([总客流], [承载量 T])

同比增幅 YoY% =
VAR 今年 = [总客流]
VAR 去年 = CALCULATE([总客流], SAMEPERIODLASTYEAR(dim_date[date]))
RETURN DIVIDE(今年 - 去年, 去年)

超载预警 = IF([日饱和度] > 0.9, "预警", "正常")

预测区间覆盖率 PICP =
DIVIDE(
    COUNTROWS(FILTER(fact_daily,
        fact_daily[visitors] >= fact_daily[pred_lower]
        && fact_daily[visitors] <= fact_daily[pred_upper])),
    COUNTROWS(fact_daily)
)
```

> 面试高频：讲清 `DIVIDE` 比 `/` 好在自动处理除零；`SAMEPERIODLASTYEAR` 做同比需要连续的日期维。

---

## 五、Power BI Desktop 执行步骤（照着做）

1. **获取数**：Power BI Desktop → 主页"获取数据" → 文本/CSV → 选 `jiuzhaigou_daily.csv`。
2. **建维度表**：在 Power Query 里从 date 派生年/月/周/季节/是否周末；节假日维可从你的节假日标记去重生成。
3. **建模**：切到"模型"视图，把 fact_daily.date 拖到 dim_date.date 建立一对多关系；同理连 dim_holiday。
4. **写度量值**：在"报表"视图右键事实表 → 新建度量值，粘贴第四节 DAX。
5. **画 4 页**：按第三节拖视觉对象 + 切片器；Page4 用"表"视觉 + 条件格式做预警高亮。
6. **发布/导出**：保存 `.pbix`；若想在线演示，可发布到 Power BI 服务（需账号）或录屏。简历附上截图 + `.pbix` 路径/GitHub。
7. **更新简历**：把"Power BI（了解）"改成"Power BI（独立搭建景区客流运营决策看板，含星型模型与 DAX 度量值）"——从"了解"变"会做"，央国企筛选通过率直接上一个台阶。

---

## 六、交付清单（做完你手上就有）

- [ ] `jiuzhaigou_daily.csv`（从你现有数据导出）
- [ ] `九寨沟客流运营决策.pbix`
- [ ] 看板截图 3-4 张（放进作品集/简历）
- [ ] 简历中 Power BI 描述升级（见第五步第 7 点）
- [ ] 一句话项目描述（和九寨沟业务闭环版共用）：
  > "同一份景区数据，用 Power BI 搭建运营决策看板（星型模型 + DAX 同比/饱和度度量 + 预警下钻），与 Streamlit 预测应用形成'预测—预警—调度'闭环。"

---

## 七、和你已有技能的衔接

- `auto-workflow` 可把这份 `.pbix` + 截图随项目一起**定时备份到 GitHub**；
- `thesis-topic-scout` 里九寨沟本就是示范选题，这份看板可直接作为毕设的"系统演示"章节素材。
