"""
九寨沟客流数据清洗与特征工程
从原始CSV（date, visitors）清洗并构建用于ML的特征
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# 使 data/ 脚本可复用 config 与 utils/ 下的共享模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_DIR, RAW_XLSX
from config import HOLIDAY_COVER_UNTIL_YEAR, NEAR_HOLIDAY_DAYS, GOLDEN_WEEK_RULES


def clean_and_featurize(input_csv="jiuzhaigou_daily.csv", output_csv="jiuzhaigou_features.csv"):
    """清洗数据并构建特征"""
    input_path = os.path.join(DATA_DIR, input_csv)
    output_path = os.path.join(DATA_DIR, output_csv)
    
    # ===== 1. 加载数据 =====
    if not os.path.exists(input_path):
        print(f"[警告] {input_csv} 不存在，请先将原始数据转换为 CSV...")
        xlsx_path = RAW_XLSX
        if os.path.exists(xlsx_path):
            print(f"  检测到原始 Excel: {os.path.basename(xlsx_path)}")
            print("  请先转换为 CSV（列需含 date, visitors）：")
            print(f"    python powerbi/xlsx_to_csv.py data/jiuzhaigou_daily_2025.xlsx data/jiuzhaigou_daily.csv")
        print("  或运行 data/jiuzhaigou_scraper.py 增量爬取最新数据。")
        raise FileNotFoundError(f"找不到数据文件 {input_csv}。")
    else:
        df = pd.read_csv(input_path, encoding="utf-8-sig")
        print(f"[1/6] 加载原始数据: {len(df)} 行")
    
    # ===== 2. 基本清洗 =====
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    
    # 剔除异常值（游客数为0或异常大的）
    q1, q3 = df["visitors"].quantile([0.01, 0.99])
    iqr = q3 - q1
    df = df[(df["visitors"] >= q1 - 1.5 * iqr) & (df["visitors"] <= q3 + 1.5 * iqr)]
    df = df[df["visitors"] > 0]
    print(f"[2/6] 清洗后: {len(df)} 行")
    print(f"  日期范围: {df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}")
    print(f"  游客量范围: {df['visitors'].min():,} ~ {df['visitors'].max():,}")
    print(f"  游客量均值: {df['visitors'].mean():,.0f}")
    
    # ===== 3. 时间特征 =====
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.dayofweek  # 0=周一, 6=周日
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["day_of_year"] = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["quarter"] = df["date"].dt.quarter
    df["is_month_start"] = df["date"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
    print(f"[3/6] 时间特征已构建 (11个特征)")
    
    # ===== 4. 节假日特征 =====
    # 统一节假日数据源：真实节假日 CSV 优先 + 未来年份简化回退
    from utils.holidays import get_holiday_set
    holidays = get_holiday_set(cover_until_year=HOLIDAY_COVER_UNTIL_YEAR)

    df["is_holiday"] = df["date"].dt.strftime("%Y-%m-%d").isin(holidays).astype(int)
    
    # 临近节假日（前后 NEAR_HOLIDAY_DAYS 天，向量化，避免逐行循环）
    holiday_dates = pd.to_datetime(list(holidays))
    near_mask = pd.Series(False, index=df.index)
    for delta in range(-NEAR_HOLIDAY_DAYS, NEAR_HOLIDAY_DAYS + 1):
        if delta == 0:
            continue
        near_mask |= df["date"].isin(holiday_dates + pd.Timedelta(days=delta))
    df["near_holiday"] = near_mask.astype(int)
    
    # 暑假 (7-8月)
    df["is_summer"] = df["month"].isin([7, 8]).astype(int)
    # 黄金周（国庆+春节），规则由 config.GOLDEN_WEEK_RULES 统一配置
    golden_mask = pd.Series(False, index=df.index)
    for month, end_day in GOLDEN_WEEK_RULES.items():
        golden_mask |= (df["month"] == month) & (df["day"] <= end_day)
    df["is_golden_week"] = golden_mask.astype(int)
    # 景区旺季 (4-11月，九寨沟旺季)
    df["is_peak_season"] = df["month"].isin([4, 5, 6, 7, 8, 9, 10, 11]).astype(int)
    
    print(f"[4/6] 节假日特征已构建")
    print(f"  节假日天数: {df['is_holiday'].sum()}")
    print(f"  黄金周天数: {df['is_golden_week'].sum()}")
    
    # ===== 5. 滞后特征（时序特征） =====
    df = df.sort_values("date").reset_index(drop=True)
    
    # 短期滞后
    for lag in [1, 2, 3, 7]:
        df[f"visitors_lag_{lag}"] = df["visitors"].shift(lag)
    
    # 滚动统计
    for window in [3, 7, 14, 30]:
        df[f"visitors_roll_mean_{window}"] = df["visitors"].rolling(window, min_periods=1).mean()
        df[f"visitors_roll_std_{window}"] = df["visitors"].rolling(window, min_periods=1).std().fillna(0)
        df[f"visitors_roll_max_{window}"] = df["visitors"].rolling(window, min_periods=1).max()
        df[f"visitors_roll_min_{window}"] = df["visitors"].rolling(window, min_periods=1).min()
    
    # 同比（365天前，如果有的话）
    df["visitors_lag_365"] = df["visitors"].shift(365)
    
    # 差分
    df["visitors_diff_1"] = df["visitors"].diff(1)
    df["visitors_diff_7"] = df["visitors"].diff(7)
    
    # 周同比变化率
    df["visitors_wow"] = df["visitors"].pct_change(7).fillna(0)
    
    # 趋势强度（7日均值比30日均值）
    df["trend_strength"] = df["visitors_roll_mean_7"] / df["visitors_roll_mean_30"].replace(0, 1)
    
    print(f"[5/6] 时序特征已构建")
    print(f"  总特征数: {len(df.columns)}")
    
    # ===== 6. 保存 =====
    # 删除无法用于预测的行（NaN过多）
    df = df.dropna(subset=[c for c in df.columns if c.startswith("visitors_lag_")])
    df = df.reset_index(drop=True)
    
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    file_size = os.path.getsize(output_path)
    print(f"[6/6] 已保存特征数据: {output_csv}")
    print(f"  行数: {len(df)}, 列数: {len(df.columns)}, 文件大小: {file_size:,} bytes")
    
    # 打印特征列表
    feature_cols = [c for c in df.columns if c not in ("date", "visitors")]
    print(f"\n特征列表 ({len(feature_cols)}个):")
    print(f"  时间特征: year, month, day, day_of_week, is_weekend, day_of_year, week_of_year, quarter, is_month_start, is_month_end")
    print(f"  节假日特征: is_holiday, near_holiday, is_summer, is_golden_week, is_peak_season")
    print(f"  滞后特征: visitors_lag_1~7, visitors_lag_365, visitors_diff_1, visitors_diff_7, visitors_wow")
    print(f"  滚动统计: visitors_roll_mean/std/max/min_3/7/14/30, trend_strength")
    
    return df


if __name__ == "__main__":
    clean_and_featurize()
