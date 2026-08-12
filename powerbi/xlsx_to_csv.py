#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把九寨沟 xlsx 转为 Power BI 脚本要的 date,visitors 中间 CSV。"""
import sys, csv, re, datetime, openpyxl

xlsx, out = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
ws = wb.active

def fmt(d):
    if isinstance(d, (datetime.datetime, datetime.date)):
        return d.strftime("%Y-%m-%d")
    return str(d).strip()

n = 0
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "visitors"])
    for row in ws.iter_rows(min_row=2, values_only=True):
        d, v = row[0], row[1]
        if d is None:
            continue
        m = re.search(r"(\d+)", str(v))
        if not m:
            continue
        w.writerow([fmt(d), m.group(1)])
        n += 1
print(f"written {n} rows -> {out}")
