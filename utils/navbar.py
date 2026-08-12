"""
共享导航栏组件 - 景区客流预测平台
统一所有页面的导航栏、标题栏和动态刷新功能
"""
import streamlit as st
import time
from datetime import datetime

def render_navbar(current_page: str = "首页"):
    """
    渲染统一的顶部导航栏和标题栏
    current_page: 当前页面名称（用于高亮）
    """
    # 统一的页面标题（固定不变）
    st.set_page_config(
        page_title="景区客流智能预测平台",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 修复侧边栏和导航栏颜色 + 隐藏默认导航 + 强制深色背景
    st.markdown("""
    <style>
        /* 强制全局深色背景 */
        .stApp {
            background: linear-gradient(135deg, #0a1628 0%, #0f2642 50%, #0a1628 100%) !important;
        }
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 1rem !important;
        }
        
        /* 全局文字颜色提升可读性 */
        .main .stMarkdown p, .main .stMarkdown li, .main .stMarkdown div {
            color: #e2e8f0;
        }
        .main [data-testid="stExpander"] > div:first-child {
            color: #e2e8f0 !important;
        }
        .main label, .main .stSelectbox label, .main .stSlider label, .main .stToggle label {
            color: #e2e8f0 !important;
        }
        
        /* 修复侧边栏背景 - 更亮更清晰 */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111d32 0%, #0d1e36 100%) !important;
            border-right: 1px solid rgba(100, 180, 255, 0.15) !important;
        }
        /* Streamlit 控件标签 - 强制可见 */
        [data-testid="stSidebar"] .stMarkdown {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stToggle label,
        [data-testid="stSidebar"] .stCheckbox label,
        [data-testid="stSidebar"] .stRadio label {
            color: #e2e8f0 !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] .stSlider [data-testid="stTickBar"] {
            color: #94a3b8 !important;
        }
        
        /* 隐藏 Streamlit 默认页面导航 */
        [data-testid="stSidebarNav"] { display: none !important; }
        
        /* Streamlit container border=True 的深色背景覆盖 */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(145deg, rgba(13,30,54,0.95) 0%, rgba(8,18,34,0.98) 100%) !important;
            border: 1px solid rgba(100, 180, 255, 0.12) !important;
            border-radius: 16px !important;
            padding: 4px 16px 10px 16px !important;
            margin-bottom: 6px !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] > div {
            border: none !important;
            box-shadow: none !important;
        }
        
        /* 面板卡片 - 深色背景 */
        .panel-card {
            background: linear-gradient(145deg, rgba(13,30,54,0.95) 0%, rgba(8,18,34,0.98) 100%) !important;
            border: 1px solid rgba(100, 180, 255, 0.12) !important;
            border-radius: 16px !important;
            padding: 24px !important;
            margin-bottom: 12px !important;
        }
        .panel-header {
            font-size: 16px;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(100, 180, 255, 0.08);
        }
        
        /* 统计卡片 */
        .stat-card {
            background: linear-gradient(145deg, rgba(15,38,66,0.9) 0%, rgba(10,22,40,0.95) 100%);
            border: 1px solid rgba(100,180,255,0.08);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: 800;
            color: #f1f5f9;
            font-family: 'Inter', sans-serif;
        }
        .stat-label {
            font-size: 11px;
            color: #cbd5e1;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }
        
        /* 顶部固定标题栏 */
        .top-header {
            background: linear-gradient(90deg, rgba(15,38,66,0.95) 0%, rgba(10,22,40,0.95) 100%);
            border: 1px solid rgba(100, 180, 255, 0.1);
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .top-header-title {
            font-size: 22px;
            font-weight: 800;
            color: #f1f5f9;
        }
        .top-header-subtitle {
            font-size: 12px;
            color: #cbd5e1;
        }
        .top-header-nav {
            display: flex;
            gap: 8px;
        }
        .nav-link {
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            color: #cbd5e1;
            background: rgba(100, 180, 255, 0.05);
            border: 1px solid rgba(100, 180, 255, 0.08);
            text-decoration: none;
            transition: all 0.2s;
        }
        .nav-link:hover {
            color: #f1f5f9;
            background: rgba(100, 180, 255, 0.1);
            border-color: rgba(100, 180, 255, 0.2);
        }
        .nav-link.active {
            color: #3b82f6;
            background: rgba(59, 130, 246, 0.1);
            border-color: rgba(59, 130, 246, 0.3);
        }
        
        /* 动态刷新指示器 */
        .live-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #34d399;
        }
        .live-dot {
            width: 8px;
            height: 8px;
            background: #34d399;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        
        /* 实时数据卡片闪烁效果 */
        @keyframes flash {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .live-card {
            animation: flash 3s ease-in-out infinite;
        }
        
        /* 标签样式 */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-green {
            background: rgba(34, 197, 94, 0.15);
            color: #34d399;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .badge-yellow {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .badge-red {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        /* 预警横幅 */
        .alert-banner {
            background: linear-gradient(145deg, rgba(16,185,129,0.08) 0%, rgba(16,185,129,0.04) 100%);
            border: 1px solid rgba(16,185,129,0.15);
            border-radius: 12px;
            padding: 14px 20px;
            margin-bottom: 12px;
        }
        .alert-banner.warning {
            background: linear-gradient(145deg, rgba(245,158,11,0.08) 0%, rgba(245,158,11,0.04) 100%);
            border-color: rgba(245,158,11,0.15);
        }
        .alert-banner.danger {
            background: linear-gradient(145deg, rgba(239,68,68,0.08) 0%, rgba(239,68,68,0.04) 100%);
            border-color: rgba(239,68,68,0.15);
        }
        
        /* KPI 卡片 */
        .kpi-card {
            background: linear-gradient(145deg, rgba(15,38,66,0.9) 0%, rgba(10,22,40,0.95) 100%);
            border: 1px solid rgba(100,180,255,0.08);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .kpi-card.warning {
            border-color: rgba(245,158,11,0.3);
            background: linear-gradient(145deg, rgba(245,158,11,0.08) 0%, rgba(10,22,40,0.95) 100%);
        }
        .kpi-card.danger {
            border-color: rgba(239,68,68,0.3);
            background: linear-gradient(145deg, rgba(239,68,68,0.08) 0%, rgba(10,22,40,0.95) 100%);
        }
        .kpi-label {
            font-size: 11px;
            color: #cbd5e1;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 800;
            color: #f1f5f9;
            margin: 8px 0;
            font-family: 'Inter', sans-serif;
        }
        .kpi-delta {
            font-size: 12px;
            font-weight: 600;
            color: #94a3b8;
        }
        .kpi-delta.up { color: #34d399; }
        .kpi-delta.down { color: #f87171; }
        
        /* 洞察卡片 */
        .insight-card {
            background: linear-gradient(145deg, rgba(59,130,246,0.05) 0%, rgba(8,18,34,0.3) 100%);
            border: 1px solid rgba(59,130,246,0.1);
            border-left: 3px solid #3b82f6;
            border-radius: 0 10px 10px 0;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        .insight-card.warning {
            background: linear-gradient(145deg, rgba(245,158,11,0.05) 0%, rgba(8,18,34,0.3) 100%);
            border-color: rgba(245,158,11,0.15);
            border-left-color: #f59e0b;
        }
        .insight-card.danger {
            background: linear-gradient(145deg, rgba(239,68,68,0.05) 0%, rgba(8,18,34,0.3) 100%);
            border-color: rgba(239,68,68,0.15);
            border-left-color: #ef4444;
        }
        .insight-title {
            font-size: 13px;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 4px;
        }
        .insight-text {
            font-size: 12px;
            color: #cbd5e1;
            line-height: 1.45;
        }
        
        /* 隐藏默认元素 */
        footer { display: none !important; }
        header { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # 获取当前时间
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 导航链接配置
    nav_items = [
        ("首页", "app"),
        ("客流分析", "flow"),
        ("智能预测", "predict"),
        ("数据洞察", "scenic"),
        ("节假日分析", "holiday"),
        ("运营决策", "decision"),
    ]
    
    # 构建导航链接 HTML
    nav_html = ""
    for name, page in nav_items:
        active_class = "active" if name == current_page else ""
        nav_html += f'<a href="/{page}" class="nav-link {active_class}">{name}</a>'
    
    # 渲染顶部标题栏
    st.markdown(f"""
    <div class="top-header">
        <div>
            <div class="top-header-title">景区客流智能预测平台</div>
            <div class="top-header-subtitle">基于 XGBoost 时序预测 | 九寨沟真实数据 | 方法论可迁移至同类5A景区</div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <div class="live-indicator">
                <div class="live-dot"></div>
                <span>实时数据</span>
            </div>
            <div class="top-header-nav">
                {nav_html}
            </div>
            <div style="font-size:11px; color:#cbd5e1;">{current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """渲染统一的侧边栏控制面板"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; margin-bottom:20px;">
            <div style="font-size:18px; font-weight:700; color:#e2e8f0;">景区客流预测平台</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:4px;">v2.2 | 九寨沟数据验证</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 导航菜单
        st.markdown("<div style='font-size:12px; color:#e2e8f0; margin-bottom:8px; font-weight:600;'>页面导航</div>", unsafe_allow_html=True)
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("首页", use_container_width=True, key="nav_home"):
                st.switch_page("app.py")
        with cols[1]:
            if st.button("客流分析", use_container_width=True, key="nav_flow"):
                st.switch_page("pages/flow.py")
        
        cols2 = st.columns(2)
        with cols2[0]:
            if st.button("智能预测", use_container_width=True, key="nav_predict"):
                st.switch_page("pages/predict.py")
        with cols2[1]:
            if st.button("数据洞察", use_container_width=True, key="nav_scenic"):
                st.switch_page("pages/scenic.py")
        cols3 = st.columns(2)
        with cols3[0]:
            if st.button("运营决策", use_container_width=True, key="nav_decision"):
                st.switch_page("pages/decision.py")
        with cols3[1]:
            if st.button("API文档", use_container_width=True, key="nav_api"):
                st.switch_page("pages/api_docs.py")
        
        cols4 = st.columns(2)
        with cols4[0]:
            if st.button("节假日分析", use_container_width=True, key="nav_holiday"):
                st.switch_page("pages/holiday.py")
        with cols4[1]:
            st.markdown("")
        
        st.markdown("---")
        st.markdown("---")
        
        # 实时刷新控制
        st.markdown("<div style='font-size:12px; color:#e2e8f0; margin-bottom:8px; font-weight:600;'>实时刷新</div>", unsafe_allow_html=True)
        
        auto_refresh = st.toggle("自动刷新数据", value=False, key="auto_refresh")
        refresh_interval = st.select_slider("刷新间隔", options=["2s", "5s", "10s", "30s"], value="5s", key="refresh_interval")
        
        if st.button("立即刷新", use_container_width=True, key="refresh_now"):
            st.rerun()
        
        st.markdown("---")
        
        # 数据源信息
        st.markdown("""
        <div style="font-size:11px; color:#cbd5e1; text-align:center; margin-top:20px;">
            <div>数据来源: jiuzhai.com</div>
            <div>模型: XGBoost v2.0</div>
            <div style="margin-top:8px; color:#e2e8f0;">2026 景区客流预测平台</div>
        </div>
        """, unsafe_allow_html=True)
        
        return auto_refresh, refresh_interval


def simulate_live_data(base_value, volatility=0.05):
    """模拟实时数据变化"""
    import random
    change = random.uniform(-volatility, volatility)
    return int(base_value * (1 + change))


def render_live_badge():
    """渲染实时数据角标"""
    st.markdown("""
    <div class="live-indicator" style="margin-bottom:12px;">
        <div class="live-dot"></div>
        <span>实时数据流</span>
    </div>
    """, unsafe_allow_html=True)
