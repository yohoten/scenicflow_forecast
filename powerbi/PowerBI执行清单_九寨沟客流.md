# Power BI 看板落地执行清单 · 九寨沟客流

> 目标：用你最强的九寨沟数据，独立搭建一个真实 `.pbix` 业务看板，
> 补上简历里"Power BI（了解）"的短板，覆盖央国企 BI 岗。
> 复用 `PowerBI看板规划_九寨沟客流.md` 的设计，本文是**可照做**的步骤。

---

## 阶段 0：准备数据（跑脚本，5 分钟）

1. 从九寨沟项目导出日度数据 `jiuzhaigou_daily.csv`（列含 `date` 与客流值，如 `visitors`）。
2. 把文件放到本清单同级目录，运行数据准备脚本：
   ```bash
   python prepare_powerbi_data.py --input jiuzhaigou_daily.csv --outdir powerbi_data
   ```
   - 自动生成 3 份 CSV：`fact_visitors.csv`（事实表）、`dim_date.csv`（日期维）、`dim_holiday.csv`（节假日维）。
   - 若已备好官方节假日表 `holidays.csv`（列 `date,name`），加 `--holidays holidays.csv`。
3. 打开 `powerbi_data/` 确认三份文件行数一致、日期连续。

---

## 阶段 1：Power BI Desktop 建模（约 30 分钟）

4. 打开 Power BI Desktop → **获取数据** → 文件夹/CSV，导入 `powerbi_data/` 三份文件。
5. **建立关系**（星型模型）：
   - `fact_visitors[date]` → `dim_date[date]`（一对多）
   - `fact_visitors[date]` → `dim_holiday[date]`（一对多）
6. 在「建模」选项卡新建以下 **DAX 度量值**（直接复制）：

   ```DAX
   总客流 = SUM(fact_visitors[visitors])
   日均客流 = AVERAGE(fact_visitors[visitors])
   峰值日客流 = MAX(fact_visitors[visitors])
   客流标准差 = STDEV.P(fact_visitors[visitors])
   ```

   ```DAX
   -- 同比：今年同日 vs 去年同日（去年同日可能为空则回退去年同期周）
   同比 YoY% =
   VAR cur = [总客流]
   VAR ly  = CALCULATE([总客流], SAMEPERIODLASTYEAR(dim_date[date]))
   RETURN IF(ly = 0, BLANK(), (cur - ly) / ly)
   ```

   ```DAX
   -- 日饱和度（需把核定最大承载量 T 设为参数 What-if，默认 4 万）
   日饱和度 S = DIVIDE([总客流], [最大承载量 T])
   超载预警 = IF([日饱和度 S] > 0.9, "超载", "正常")
   ```

   ```DAX
   -- 预测区间覆盖率（若导入了预测值列，回测真实值落在区间内的比例）
   PICP = 
   AVERAGEX(fact_visitors,
       IF(fact_visitors[visitors] >= fact_visitors[lower]
          && fact_visitors[visitors] <= fact_visitors[upper], 1, 0))
   ```

7. 把 `[最大承载量 T]` 做成 **What-if 参数**（建模 → 新建参数，0~80000，增量 1000，默认 40000）。

---

## 阶段 2：搭建 4 个页面（约 1 小时）

| 页面 | 主要视觉对象 | 说明 |
|------|-------------|------|
| ① 总览 KPI | 卡片图：总客流/日均/峰值/标准差 + 年份切片器 | 一眼看全局 |
| ② 趋势与预测 | 折线图（日期×客流）+ 区间带（若有预测列） | 叠加 `dim_date[year]` 图例做同比 |
| ③ 因素分析 | 柱状图：按 `weekday_name` / `is_weekend` / `is_holiday` 汇总客流 | 回答"周几/节假日更高" |
| ④ 运营预警表 | 表视觉：date / 日饱和度 S / 超载预警，筛选 S>0.9 | 直接给出限流清单 |

8. 统一主题色（建议蓝系 `#3B82F6`，与作品集一致），设好标题与筛选器。

---

## 阶段 3：收尾与展示（20 分钟）

9. **发布**：文件 → 发布到 Power BI 服务（需账号），或用 **Power BI Desktop 导出 PDF/截图** 放作品集。
10. 在作品集首页「企业监控大屏」卡片下补一行：「另独立搭建 Power BI 业务看板（九寨沟客流）」+ 截图/链接。
11. 简历把"Power BI（了解）"改为"**独立搭建 Power BI 业务看板（DAX 度量值 + 星型模型）**"——这是实打实的证据。

---

## 你被问到时怎么说（面试口径）
- "我用九寨沟 1,869 天真实数据，在 Power BI 里建了**星型模型**（事实表 + 日期/节假日维），
  写了日饱和度、同比、超载预警等 DAX 度量值，落地了'预测→预警→调度'的决策看板。"
- 硬伤预防：若被问"最大承载量 T 哪来的"——答"按景区公开规定参数化，做成 What-if 可调"；
  若被问"节假日怎么标"——答"用官方节假日表注入，未注入时仅区分周末"。诚实最稳。
