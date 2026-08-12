"""节假日模块测试：真实数据优先 + 未来年份简化回退。"""
import os
import sys

# 确保项目根目录可被导入（config / utils 等共享模块）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.holidays import get_holiday_map, get_holiday_set, get_holiday_name, is_holiday


def test_real_holiday_loaded():
    """真实节假日数据应能加载（2023-10-01 国庆）。"""
    m = get_holiday_map(2023)
    assert "2023-10-01" in m
    assert "国庆" in m["2023-10-01"]


def test_fallback_holiday_covered():
    """真实数据未覆盖的年份应有简化回退（2027-01-01 元旦）。"""
    m = get_holiday_map(2027)
    assert "2027-01-01" in m


def test_holiday_set():
    """get_holiday_set 应返回日期集合。"""
    s = get_holiday_set(2027)
    assert "2027-01-01" in s
    assert isinstance(s, set)


def test_get_holiday_name_and_is_holiday():
    """节日名查询与节假日判断。"""
    assert get_holiday_name("2023-10-01", 2023) is not None
    assert is_holiday("2023-10-01", 2023)
    assert not is_holiday("2023-06-01", 2023)
