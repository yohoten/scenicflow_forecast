"""
统一节假日数据源模块
============================================
以真实节假日数据（powerbi/holidays_2019_2025.csv）为优先数据源，
对未覆盖的未来年份回退到内置简化规则（农历近似），供特征工程、预测、
节假日分析页共用，避免各处硬编码日期不一致。

用法:
    from utils.holidays import get_holiday_map, get_holiday_set, get_holiday_name
"""
import os
import sys
import functools
from datetime import datetime, timedelta

# 统一节假日数据源路径由 config 管理
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import HOLIDAYS_CSV as HOLIDAY_CSV
from config import HOLIDAY_COVER_UNTIL_YEAR

# ===== 未来年份简化回退规则（农历近似，仅当真实数据未覆盖时使用） =====
# 格式: {节日名: [(月, 日, 持续天数), ...]}
_FALLBACK_RULES = {
    "元旦": [(1, 1, 1)],
    "春节": [(2, 1, 5)],
    "清明": [(4, 5, 1)],
    "劳动节": [(5, 1, 5)],
    "端午": [(6, 6, 1)],
    "中秋": [(9, 15, 1)],
    "国庆": [(10, 1, 7)],
}

# 真实数据覆盖的年份范围
_REAL_START_YEAR = 2019
_REAL_END_YEAR = 2025


@functools.lru_cache(maxsize=1)
def _load_real_holiday_map():
    """从真实节假日 CSV 加载 {日期: 节日名}，处理 UTF-8 BOM。
    仅依赖标准库 csv，保证该模块可独立运行与复用。"""
    holiday_map = {}
    if os.path.exists(HOLIDAY_CSV):
        import csv
        try:
            with open(HOLIDAY_CSV, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                next(reader, None)  # 跳过表头
                for row in reader:
                    if len(row) >= 2:
                        date_str = row[0].strip()
                        name = row[1].strip()
                        if date_str and name and len(date_str) == 10:
                            holiday_map[date_str] = name
        except Exception as e:  # 数据异常时回退到简化规则
            print(f"[节假日模块] 真实节假日数据加载失败: {e}，将使用简化规则")
    return holiday_map

def _build_fallback_map(cover_until_year):
    """为真实数据未覆盖的年份构建简化节假日映射。"""
    holiday_map = {}
    for year in range(_REAL_START_YEAR, cover_until_year + 1):
        # 真实数据已覆盖的年份跳过（真实优先）
        if _REAL_START_YEAR <= year <= _REAL_END_YEAR:
            continue
        for name, rules in _FALLBACK_RULES.items():
            for (month, day, days) in rules:
                for i in range(days):
                    d = datetime(year, month, day) + timedelta(days=i)
                    holiday_map[d.strftime("%Y-%m-%d")] = name
    return holiday_map


def get_holiday_map(cover_until_year=HOLIDAY_COVER_UNTIL_YEAR):
    """
    获取 {日期: 节日名} 映射。
    真实节假日优先，未来年份自动用简化规则补齐。
    """
    holiday_map = dict(_load_real_holiday_map())
    holiday_map.update(_build_fallback_map(cover_until_year))
    return holiday_map


def get_holiday_set(cover_until_year=HOLIDAY_COVER_UNTIL_YEAR):
    """获取节假日日期集合（仅含放假日期，不含补班）。"""
    return set(get_holiday_map(cover_until_year).keys())


def get_holiday_name(date, cover_until_year=HOLIDAY_COVER_UNTIL_YEAR):
    """
    获取某日期的节日名，非节假日返回 None。
    date 支持: datetime / date / "YYYY-MM-DD" 字符串
    """
    if isinstance(date, str):
        date_str = date
    elif isinstance(date, (datetime,)):
        date_str = date.strftime("%Y-%m-%d")
    else:
        try:
            date_str = date.strftime("%Y-%m-%d")
        except AttributeError:
            date_str = str(date)
    return get_holiday_map(cover_until_year).get(date_str)


def is_holiday(date, cover_until_year=HOLIDAY_COVER_UNTIL_YEAR):
    """判断某日期是否为法定节假日。"""
    return get_holiday_name(date, cover_until_year) is not None


if __name__ == "__main__":
    # 简易自检
    m = get_holiday_map(2027)
    print(f"节假日总天数: {len(m)}")
    print(f"覆盖年份: {_REAL_START_YEAR}-{_REAL_END_YEAR} (真实) + {_REAL_END_YEAR+1}-2027 (简化回退)")
    for d in ["2023-10-01", "2024-02-10", "2026-10-01", "2027-05-01", "2023-10-08"]:
        print(f"  {d} -> {m.get(d, '非节假日')}")
