# -*- coding: utf-8 -*-
"""增量版爬虫 - 每页实时保存，不怕中断"""
import re, time, csv, os, sys
from urllib.request import Request, urlopen

BASE_URL = 'https://www.jiuzhai.com/news/number-of-tourists'
# 输出到脚本所在目录（data/），保证 clean_data.py 能按默认路径读取
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jiuzhaigou_daily.csv')

# 加载已有数据
existing = {}
if os.path.exists(OUTPUT):
    with open(OUTPUT, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[row['date']] = int(row['visitors'])
    print(f'[LOAD] 已有 {len(existing)} 条数据', flush=True)

new_count = 0
consecutive_empty = 0

for start in range(0, 10000, 20):
    html = None
    for attempt in range(3):
        try:
            url = f'{BASE_URL}?start={start}'
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                html = None

    if html is None:
        print(f'[SKIP] start={start}: 请求失败', flush=True)
        consecutive_empty += 1
        if consecutive_empty > 3:
            break
        continue

    # 解析
    rows = re.split(r'(<tr[^>]*>)', html)
    page_data = []
    for i in range(len(rows)):
        vm = re.search(r'九寨沟景区共接待(\d+)人次', rows[i])
        if not vm:
            continue
        count = int(vm.group(1))
        date_str = None
        for j in range(i, min(i + 6, len(rows))):
            dm = re.search(r'(\d{4}-\d{2}-\d{2})', rows[j])
            if dm and 2010 <= int(dm.group(1)[:4]) <= 2030:
                date_str = dm.group(1)
                break
        if date_str and date_str not in existing:
            page_data.append((date_str, count))
            existing[date_str] = count

    # 立即写入
    if page_data:
        with open(OUTPUT, 'a', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            if os.path.getsize(OUTPUT) == 0:
                w.writerow(['date', 'visitors'])
            for d, c in page_data:
                w.writerow([d, c])
        new_count += len(page_data)
        consecutive_empty = 0
        print(f'[OK] start={start}: +{len(page_data)}条新增, 总计{len(existing)}条', flush=True)
    else:
        consecutive_empty += 1
        print(f'[EMP] start={start}: 无新增, 连续{consecutive_empty}页', flush=True)
        if consecutive_empty > 3:
            print(f'[END] 连续4页无新增数据，结束', flush=True)
            break

    time.sleep(0.5)

# 排序保存
print(f'\n[FINAL] 总计 {len(existing)} 条, 本次新增 {new_count} 条', flush=True)
all_sorted = sorted(existing.items())
with open(OUTPUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['date', 'visitors'])
    for d, c in all_sorted:
        w.writerow([d, c])
size = os.path.getsize(OUTPUT)
print(f'[SAVE] {OUTPUT} ({size:,} bytes)', flush=True)
print(f'[RANGE] {all_sorted[0][0]} ~ {all_sorted[-1][0]}', flush=True)
