-- ============================================================================
-- 电商用户 RFM 分析与复购率（窗口函数版）
-- 数据源：UCI Online Retail（英国电商交易，约 39 万条）
-- 表名假设：online_retail
-- 字段：InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
--       UnitPrice, CustomerID, Country
-- 兼容：SQLite 3.25+ / MySQL 8.0+ / PostgreSQL 12+
--       ⚠ 仅「日期差」函数因方言不同需替换，见各段「方言备注」
-- ============================================================================

-- 0) 清洗视图 clean：去掉退货单(C 开头)、负数量、无效客户、零单价
--    抽成 VIEW 而非 CTE，因为 CTE 作用域仅限「单条语句」；
--    下面的分群 / 复购率 / LAG / RANK 各段都要复用 clean，故建为视图。
DROP VIEW IF EXISTS clean;
CREATE VIEW clean AS
SELECT
    CustomerID,
    InvoiceNo,
    StockCode,
    InvoiceDate,
    Quantity,
    UnitPrice,
    Country,
    Quantity * UnitPrice AS amount
FROM online_retail
WHERE CustomerID IS NOT NULL
  AND Quantity   > 0
  AND UnitPrice  > 0
  AND InvoiceNo NOT LIKE 'C%';   -- 退货/取消单以 C 开头

-- 1) 每位客户的 RFM 基础值 + 打分 + 分群标签（RF 矩阵）
--    方言备注：日期差
--      SQLite     : julianday(a) - julianday(b)
--      MySQL      : DATEDIFF(a, b)
--      PostgreSQL : (a - b)
WITH rfm_raw AS (
    SELECT
        CustomerID,
        -- Recency：最近一次购买距「数据内最新日」的天数（比 now() 更稳，可复现）
        CAST(
            julianday((SELECT MAX(InvoiceDate) FROM clean))
          - julianday(MAX(InvoiceDate))
        AS INT)                                                      AS recency,
        COUNT(DISTINCT InvoiceNo)                                    AS frequency,
        ROUND(SUM(amount), 2)                                        AS monetary
    FROM clean
    GROUP BY CustomerID
),
-- 2) RFM 打分（1–5 分）。Recency 越小越好 → 反向打分
scored AS (
    SELECT
        CustomerID,
        recency, frequency, monetary,
        -- Recency 升序分桶：天数越少分越高（6 - NTILE 实现反向）
        6 - NTILE(5) OVER (ORDER BY recency)   AS R,
        NTILE(5) OVER (ORDER BY frequency)     AS F,
        NTILE(5) OVER (ORDER BY monetary)      AS M
    FROM rfm_raw
),
-- 3) 组合分群标签（RF 矩阵，最常用、最直观）
segmented AS (
    SELECT
        CustomerID, recency, frequency, monetary, R, F, M,
        CASE
            WHEN R >= 4 AND F >= 4 THEN '重要价值客户'
            WHEN R >= 4 AND F < 4 THEN '重要发展客户'
            WHEN R < 4 AND F >= 4 THEN '重要保持客户'
            ELSE                         '一般客户'
        END AS segment
    FROM scored
)
-- 输出：各分群人数与平均消费额
SELECT
    segment,
    COUNT(*)                    AS customers,
    ROUND(AVG(monetary), 2)     AS avg_monetary,
    ROUND(AVG(recency), 1)      AS avg_recency_days
FROM segmented
GROUP BY segment
ORDER BY customers DESC;


-- 4) 复购率 = 购买次数 >= 2 的客户占比
--    （面试高频题：用 COUNT(DISTINCT) + 条件聚合，无需自连接）
WITH order_count AS (
    SELECT CustomerID, COUNT(DISTINCT InvoiceNo) AS orders
    FROM clean
    GROUP BY CustomerID
)
SELECT
    COUNT(*)                                                       AS total_customers,
    SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END)                  AS repeat_customers,
    ROUND(100.0 * SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END)
                / COUNT(*), 2)                                     AS repurchase_rate_pct
FROM order_count;


-- 5) 客户两次购买间隔（LAG 窗口函数示例）
--    方言备注：日期差同段 1
WITH customer_orders AS (
    SELECT
        CustomerID,
        MIN(InvoiceDate)        AS order_date,
        ROW_NUMBER() OVER (PARTITION BY CustomerID ORDER BY MIN(InvoiceDate)) AS rn
    FROM clean
    GROUP BY CustomerID, InvoiceNo
)
SELECT
    CustomerID,
    order_date,
    CAST(
        julianday(order_date)
      - julianday(LAG(order_date) OVER (PARTITION BY CustomerID ORDER BY order_date))
    AS INT) AS gap_days
FROM customer_orders
WHERE rn > 1
ORDER BY CustomerID, order_date
LIMIT 50;


-- 6) 各国销售额 Top 3 品类（RANK 窗口函数 + 子查询过滤）
WITH sales AS (
    SELECT Country, StockCode, SUM(amount) AS amt
    FROM clean
    GROUP BY Country, StockCode
)
SELECT Country, StockCode, amt, rk
FROM (
    SELECT
        Country, StockCode, amt,
        RANK() OVER (PARTITION BY Country ORDER BY amt DESC) AS rk
    FROM sales
) t
WHERE rk <= 3
ORDER BY Country, rk;


-- ============================================================================
-- 使用说明
--   SQLite ：sqlite3 db.sqlite < rfm_analysis.sql
--   MySQL  ：将 julianday(a)-julianday(b) 替换为 DATEDIFF(a,b)，语句整体可直接跑
--   Postgres：将 julianday(...) 替换为 (...)::date 相减，其余不变
-- 建议索引（大数据量时）：
--   CREATE INDEX idx_cust ON online_retail(CustomerID);
--   CREATE INDEX idx_inv  ON online_retail(InvoiceNo, InvoiceDate);
-- 说明：clean 为复用视图，无需在每条语句里重复写清洗逻辑。
-- ============================================================================
