"""
承载率分级与运营标签共享逻辑
============================================
统一「正常 / 预警 / 高危」分级判定与徽标/文案映射，
避免各页面（首页、预测、决策）阈值与文案漂移。
"""
from config import CAPACITY, WARNING_RATIO, DANGER_RATIO

# 等级 -> 徽标 CSS 类（对应 utils/navbar.py 的 .badge-* 样式）
LEVEL_BADGE_CLASS = {
    "normal": "badge badge-green",
    "warning": "badge badge-yellow",
    "danger": "badge badge-red",
}

# 等级 -> 中文文案
LEVEL_LABEL = {
    "normal": "正常",
    "warning": "预警",
    "danger": "高负荷",
}

# 等级 -> 图标（可访问性辅助，色盲友好）
LEVEL_ICON = {
    "normal": "🟢",
    "warning": "🟡",
    "danger": "🔴",
}


def load_level(visitors: float, capacity: float = CAPACITY) -> str:
    """根据客流与承载量返回等级: 'normal' / 'warning' / 'danger'。"""
    if visitors > capacity * DANGER_RATIO:
        return "danger"
    if visitors > capacity * WARNING_RATIO:
        return "warning"
    return "normal"


def load_label(level: str) -> str:
    """返回等级中文文案（含图标，可访问性友好）。"""
    return f"{LEVEL_ICON.get(level, '')} {LEVEL_LABEL.get(level, level)}"


def badge_html(level: str, label: str | None = None) -> str:
    """返回对应等级徽标的 HTML 片段（含图标）。"""
    cls = LEVEL_BADGE_CLASS.get(level, "badge")
    text = label or LEVEL_LABEL.get(level, level)
    icon = LEVEL_ICON.get(level, "")
    return f'<span class="{cls}">{icon} {text}</span>'
