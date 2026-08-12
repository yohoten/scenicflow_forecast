#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_powerbi_data.py
-----------------------
读取景区日度客流原始数据（jiuzhaigou_daily.csv），生成 Power BI 所需的
「事实表 + 日期维表 + 节假日维表」三份 CSV，可直接在 Power BI Desktop 中建模。

设计原则：
  * 仅用 Python 标准库（csv / datetime / argparse），无第三方依赖，
    可在任意环境运行（含 WorkBuddy 内置 Python）。
  * 节假日不硬编码具体日期（避免编造导致硬伤）；如需节假日标记，
    用 --holidays 传入官方节假日 CSV（列：date, name），否则仅标记周末。
  * 自动探测日期列与客流值列，缺失值/解析失败会显式报错。

用法：
  python prepare_powerbi_data.py --input jiuzhaigou_daily.csv --outdir powerbi_data
  python prepare_powerbi_data.py --input jiuzhaigou_daily.csv \
        --date-col date --value-col visitors --holidays holidays_2019_2023.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MONTH_CN = ["一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"]


def detect_columns(header, date_col, value_col):
    """日期列默认取含 date/日期 的列；值列优先用指定名，否则取第一个数值列。"""
    lower = [h.strip().lower() for h in header]
    if date_col is None:
        for h, l in zip(header, lower):
            if "date" in l or "日期" in l or "时间" in l:
                date_col = h
                break
    if date_col is None:
        raise SystemExit("✗ 未找到日期列，请用 --date-col 指定（如 date / 日期）")

    if value_col is None:
        # 跳过日期列，挑第一个看起来像数值的列
        candidates = ["visitors", "visitor", "客流", "客流数", "count", "value", "人数"]
        for h, l in zip(header, lower):
            if h == date_col:
                continue
            if any(c in l for c in candidates):
                value_col = h
                break
        if value_col is None:  # 退而求其次：第一个非日期列
            for h in header:
                if h != date_col:
                    value_col = h
                    break
    if value_col is None or value_col not in header:
        raise SystemExit(f"✗ 未找到客流值列，请用 --value-col 指定（如 visitors / 客流）")
    return date_col, value_col


def parse_date(s):
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {s!r}（支持 YYYY-MM-DD 等格式）")


def load_holidays(path):
    """读取节假日 CSV（date, name），返回 {date_str: name}。"""
    holi = {}
    if not path:
        return holi
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = parse_date(row["date"]).strftime("%Y-%m-%d")
            holi[d] = row.get("name", "节假日").strip() or "节假日"
    return holi


def main():
    ap = argparse.ArgumentParser(description="生成 Power BI 数据（事实表+日期维+节假日维）")
    ap.add_argument("--input", required=True, help="原始日度客流 CSV")
    ap.add_argument("--outdir", default="powerbi_data", help="输出目录（默认 ./powerbi_data）")
    ap.add_argument("--date-col", default=None, help="日期列名（默认自动探测）")
    ap.add_argument("--value-col", default=None, help="客流值列名（默认自动探测）")
    ap.add_argument("--holidays", default=None, help="可选：官方节假日 CSV（date,name）")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        raise SystemExit(f"✗ 输入文件不存在: {args.input}")

    # 读原始数据
    rows = []
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        date_col, value_col = detect_columns(header, args.date_col, args.value_col)
        for i, row in enumerate(reader, 2):  # 行号从 2 起（含表头）
            raw_d = row.get(date_col, "")
            raw_v = row.get(value_col, "")
            if raw_d == "" or raw_v == "":
                print(f"  ⚠ 第 {i} 行缺失，跳过：date={raw_d!r} value={raw_v!r}")
                continue
            try:
                dt = parse_date(raw_d)
                val = float(raw_v)
            except Exception as e:
                print(f"  ⚠ 第 {i} 行解析失败，跳过：{e}")
                continue
            rows.append((dt, val, row))

    if not rows:
        raise SystemExit("✗ 无有效数据行，请检查 CSV 格式")
    rows.sort(key=lambda r: r[0])

    holi = load_holidays(args.holidays)
    os.makedirs(args.outdir, exist_ok=True)

    # 额外保留的非日期、非客流数值列（一并进事实表，便于 Power BI 下钻）
    extra_cols = [h for h in header if h not in (date_col, value_col)]
    numeric_extras = []
    for h in extra_cols:
        if all(_is_number(r[2].get(h, "")) for r in rows[: min(50, len(rows))]):
            numeric_extras.append(h)

    # 1) 事实表 fact_visitors.csv
    fact_path = os.path.join(args.outdir, "fact_visitors.csv")
    with open(fact_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "visitors"] + numeric_extras)
        for dt, val, raw in rows:
            w.writerow([dt.strftime("%Y-%m-%d"), f"{val:.0f}"]
                       + [raw.get(c, "") for c in numeric_extras])

    # 2) 日期维表 dim_date.csv
    dim_path = os.path.join(args.outdir, "dim_date.csv")
    with open(dim_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "year", "quarter", "month", "month_name",
                    "week_of_year", "weekday", "weekday_name", "is_weekend",
                    "day_of_year", "is_month_start", "is_month_end"])
        for dt, _, _ in rows:
            iso = dt.isocalendar()
            w.writerow([
                dt.strftime("%Y-%m-%d"),
                dt.year,
                (dt.month - 1) // 3 + 1,
                dt.month,
                MONTH_CN[dt.month - 1],
                iso[1],
                dt.weekday(),
                WEEKDAY_CN[dt.weekday()],
                "是" if dt.weekday() >= 5 else "否",
                dt.timetuple().tm_yday,
                "是" if dt.day == 1 else "否",
                "是" if dt.day == _last_day(dt) else "否",
            ])

    # 3) 节假日维表 dim_holiday.csv
    holi_path = os.path.join(args.outdir, "dim_holiday.csv")
    with open(holi_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "holiday_name", "is_holiday"])
        for dt, _, _ in rows:
            d = dt.strftime("%Y-%m-%d")
            name = holi.get(d, "")
            w.writerow([d, name, "是" if name else "否"])

    total = sum(r[1] for r in rows)
    print(f"✓ 完成。共 {len(rows)} 天，区间 {rows[0][0].date()} ~ {rows[-1][0].date()}")
    print(f"  总客流：{total:,.0f}")
    print(f"  事实表：{fact_path}")
    print(f"  日期维：{dim_path}")
    print(f"  节假日维：{holi_path}"
          + (f"（已标记 {len(holi)} 个节假日）" if holi else "（未提供节假日，仅标记周末）"))
    if not holi:
        print("  💡 提示：传入 --holidays holidays.csv（官方节假日，列 date,name）"
              "可在 Power BI 中区分法定节假日与周末。")


def _is_number(s):
    try:
        float(str(s).strip())
        return True
    except (ValueError, TypeError):
        return False


def _last_day(dt):
    # 返回当月最后一天
    if dt.month == 12:
        nxt = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        nxt = dt.replace(month=dt.month + 1, day=1)
    return (nxt - timedelta(days=1)).day


if __name__ == "__main__":
    main()
