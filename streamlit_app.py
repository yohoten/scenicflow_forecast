import logging
import time as _time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import CAPACITY, WARNING_RATIO, DANGER_RATIO, PEAK_RATIO
from utils.levels import load_level, badge_html
from utils.navbar import render_navbar, render_sidebar
from utils.predictor import (
    predict_next_7_days, get_model_metrics, get_feature_importance,
    generate_historical_trend, is_model_ready,
)

logger = logging.getLogger(__name__)

render_navbar("首页")
auto_refresh, refresh_interval = render_sidebar()


# ========== 数据加载（带缓存，避免自动刷新重复读 CSV / 重建特征） ==========
@st.cache_data(ttl=300, show_spinner=False)
def load_historical(days: int = 365) -> pd.DataFrame:
    """历史客流趋势（缓存 5 分钟）。"""
    return generate_historical_trend(days)


@st.cache_data(ttl=300, show_spinner=False)
def load_forecast() -> pd.DataFrame:
    """未来 7 日预测（缓存 5 分钟）。"""
    return predict_next_7_days()


with st.spinner("正在加载数据与模型…"):
    model_ready = is_model_ready()
    metrics = get_model_metrics()
    hist_df = load_historical(365)
    forecast_df = load_forecast()

# 数据加载状态
if not model_ready:
    st.warning("模型文件未找到，当前展示模拟数据。请运行 ml/train_model.py 训练模型。")

# 数据校验
if hist_df.empty:
    st.error("历史数据加载失败，请检查 data/ 目录下是否存在 jiuzhaigou_daily.csv 或 jiuzhaigou_features.csv")
    st.stop()

if forecast_df.empty:
    st.error("预测数据生成失败，请检查模型文件是否存在")
    st.stop()

# ========== 时间范围选择 ==========
days_map = {"近30天": 30, "近90天": 90, "近180天": 180, "近1年": 365, "全部数据": 9999}
range_label = st.radio(
    "时间范围", list(days_map.keys()),
    index=len(days_map) - 1, horizontal=True,
    help="切换主图、明细表与客流分布的时间跨度"
)
selected_days = days_map[range_label]
if selected_days < 9999 and not hist_df.empty:
    cutoff = hist_df["日期"].max() - timedelta(days=selected_days)
    display_df = hist_df[hist_df["日期"] >= cutoff].copy()
else:
    display_df = hist_df.copy()

# 数据更新日期标注（“今日客流”实为数据最后一天，避免误导）
if not display_df.empty:
    data_date = display_df["日期"].iloc[-1]
    lag_days = (datetime.now() - data_date).days
    lag_text = f"（{lag_days} 天前更新）" if lag_days >= 0 else ""
    st.caption(f"📅 数据更新至 {data_date:%Y-%m-%d} {lag_text}")

# ========== 承载率与告警横幅 ==========
if not display_df.empty:
    today_val = display_df["客流量"].iloc[-1]
    today_level = load_level(today_val)
else:
    today_val = 0
    today_level = "normal"

alert_html = {
    "danger": (
        '<div class="alert-banner">'
        '<div style="font-weight: 700; color: #f87171; font-size: 14px;">🔴 红色预警：当前客流接近承载上限</div>'
        '<div style="font-size: 12px; color: #cbd5e1;">建议立即启动限流措施，增派安保人员，并通过广播引导游客错峰游览</div>'
        '</div>'
    ),
    "warning": (
        '<div class="alert-banner warning">'
        '<div style="font-weight: 700; color: #fbbf24; font-size: 14px;">🟡 黄色预警：客流处于较高水平</div>'
        '<div style="font-size: 12px; color: #cbd5e1;">建议密切关注重点区域人流密度，提前做好疏导准备</div>'
        '</div>'
    ),
    "normal": (
        '<div class="alert-banner normal">'
        '<div style="font-weight: 700; color: #34d399; font-size: 14px;">🟢 运营正常：客流处于安全区间</div>'
        '<div style="font-size: 12px; color: #cbd5e1;">当前客流平稳，建议维持现有运营策略</div>'
        '</div>'
    ),
}
st.markdown(alert_html[today_level], unsafe_allow_html=True)

# ========== KPI 计算 ==========
if not display_df.empty:
    yesterday_val = display_df["客流量"].iloc[-2] if len(display_df) > 1 else today_val
    week_ago_val = display_df["客流量"].iloc[-8] if len(display_df) > 7 else today_val
    month_ago_val = display_df["客流量"].iloc[-31] if len(display_df) > 30 else today_val
    day_change = ((today_val - yesterday_val) / yesterday_val * 100) if yesterday_val > 0 else 0
    week_change = ((today_val - week_ago_val) / week_ago_val * 100) if week_ago_val > 0 else 0
    month_change = ((today_val - month_ago_val) / month_ago_val * 100) if month_ago_val > 0 else 0
    avg_val = display_df["客流量"].mean()
    max_val = display_df["客流量"].max()
    min_val = display_df["客流量"].min()
else:
    today_val = avg_val = max_val = min_val = 0
    day_change = week_change = month_change = 0

kpi_data = [
    ("TODAY", f"{today_val:,.0f}", "今日客流", f"{day_change:+.1f}%", day_change, "人次"),
    ("WEEK", f"{avg_val:,.0f}", "7日均值", f"{week_change:+.1f}%", week_change, "人次"),
    ("MAX", f"{max_val:,.0f}", "历史最高", "", 0, "人次"),
    ("MIN", f"{min_val:,.0f}", "历史最低", "", 0, "人次"),
    ("R²", f"{metrics.get('r2', '—')}", "模型准确度", f"MAE {metrics.get('mae', 0):,.0f}" if isinstance(metrics.get('mae'), (int, float)) else "MAE —", 0, ""),
    ("MAPE", f"{metrics.get('mape', 0):.1f}%" if isinstance(metrics.get('mape'), (int, float)) else "—", "预测误差率", "", 0, ""),
]

# KPI 卡片（3×2 响应式布局，窄屏更友好）
for row_start in range(0, 6, 3):
    kpi_cols = st.columns(3)
    for j, (kpi_id, value, label, delta, delta_val, unit) in enumerate(kpi_data[row_start:row_start + 3]):
        with kpi_cols[j]:
            card_class = ""
            if kpi_id == "TODAY" and today_level != "normal":
                card_class = today_level
            delta_class = "up" if delta_val > 0 else "down" if delta_val < 0 else ""
            delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ''
            st.markdown(f"""
            <div class="kpi-card {card_class}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}<span style="font-size:14px; color:#cbd5e1; margin-left:4px;">{unit}</span></div>
                {delta_html}
            </div>
            """, unsafe_allow_html=True)

# ========== 主图 + 未来7日预测 ==========
chart_col1, chart_col2 = st.columns([7, 3])

with chart_col1:
    with st.container(border=True):
        st.markdown('<div class="panel-header">客流趋势与预测</div>', unsafe_allow_html=True)
        try:
            last_hist_date = display_df["日期"].iloc[-1]
            forecast_dates = pd.to_datetime([last_hist_date + timedelta(days=i + 1) for i in range(len(forecast_df))])

            fig = go.Figure()

            # 历史客流
            fig.add_trace(go.Scatter(
                x=display_df["日期"], y=display_df["客流量"], mode="lines", name="历史客流",
                line=dict(color="#3b82f6", width=2), fill="tozeroy", fillcolor="rgba(59,130,246,0.1)",
                hovertemplate="<b>%{x}</b><br>客流: %{y:,.0f} 人次<extra></extra>"
            ))

            # 预测客流
            fig.add_trace(go.Scatter(
                x=forecast_dates, y=forecast_df["预测"], mode="lines+markers", name="预测客流",
                line=dict(color="#06b6d4", width=2.5), marker=dict(size=8, color="#06b6d4", line=dict(color="white", width=2)),
                hovertemplate="<b>%{x}</b><br>预测: %{y:,.0f} 人次<extra></extra>"
            ))

            # 置信区间
            fig.add_trace(go.Scatter(
                x=list(forecast_dates) + list(forecast_dates)[::-1],
                y=list(forecast_df["上限"]) + list(forecast_df["下限"])[::-1],
                fill="toself", fillcolor="rgba(6,182,212,0.15)", line=dict(color="rgba(0,0,0,0)"), name="置信区间", hoverinfo="skip"
            ))

            # 预警线（70%）与承载上限线（100%），形成绿-黄-红区带
            fig.add_hline(
                y=CAPACITY * WARNING_RATIO, line_dash="dot", line_color="#fbbf24", line_width=1,
                annotation_text=f"预警线 {int(CAPACITY * WARNING_RATIO):,}", annotation_position="right",
                annotation_font_color="#fbbf24", annotation_font_size=11
            )
            fig.add_hline(
                y=CAPACITY, line_dash="dash", line_color="#ef4444", line_width=1,
                annotation_text=f"承载上限 {CAPACITY:,}", annotation_position="right",
                annotation_font_color="#ef4444", annotation_font_size=11
            )

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#cbd5e1", size=11), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=40, r=40, t=60, b=40), height=420, hovermode="x unified", showlegend=True,
                xaxis=dict(showgrid=False, zeroline=False, title="日期", title_font_color="#cbd5e1"),
                yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", zeroline=False, tickformat=",", title="客流量（人次）", title_font_color="#cbd5e1"),
            )

            st.plotly_chart(fig, use_container_width=True, height=420, key="home_main_chart",
                            config={"displayModeBar": False, "responsive": True,
                                    "toImageButtonOptions": {"format": "png", "scale": 2}})
        except Exception:
            logger.exception("首页主图渲染失败")
            st.error("图表渲染出错，请刷新页面重试")
            st.info("如持续出现该问题，请检查数据文件或浏览器控制台")

with chart_col2:
    with st.container(border=True):
        st.markdown('<div class="panel-header">未来7日预测</div>', unsafe_allow_html=True)
        if not forecast_df.empty:
            for _, row in forecast_df.iterrows():
                date_str = row["日期"]
                pred = row["预测"]
                upper = row["上限"]
                lower = row["下限"]
                badge = badge_html(load_level(pred))
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid rgba(100,180,255,0.06);">
                    <div>
                        <div style="font-size:13px; font-weight:600; color:#e2e8f0;">{date_str}</div>
                        <div style="font-size:11px; color:#cbd5e1;">{lower:,.0f} - {upper:,.0f}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:16px; font-weight:700; color:#06b6d4;">{pred:,.0f}</div>
                        <div style="margin-top:2px;">{badge}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # 模型性能（折叠，运营非高频关注）
    with st.expander("模型性能", expanded=False):
        if metrics:
            perf_items = [
                ("R2 决定系数", f"{metrics.get('r2', '—')}", "越接近1越好"),
                ("MAE 平均误差", f"{metrics.get('mae', 0):,.0f} 人次" if isinstance(metrics.get('mae'), (int, float)) else "MAE —", "预测偏差均值"),
                ("RMSE 均方根误差", f"{metrics.get('rmse', 0):,.0f} 人次" if isinstance(metrics.get('rmse'), (int, float)) else "RMSE —", "大误差惩罚"),
                ("MAPE 误差率", f"{metrics.get('mape', 0):.1f}%" if isinstance(metrics.get('mape'), (int, float)) else "MAPE —", "相对误差百分比"),
            ]
            for label, val, desc in perf_items:
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid rgba(100,180,255,0.06);">
                    <div>
                        <div style="font-size:12px; color:#cbd5e1;">{label}</div>
                        <div style="font-size:11px; color:#cbd5e1;">{desc}</div>
                    </div>
                    <div style="font-size:16px; font-weight:700; color:#f1f5f9;">{val}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("模型未就绪，暂无指标数据")

# ========== 特征重要性 + 智能洞察 ==========
feat_col, insight_col = st.columns([5, 3])

with feat_col:
    with st.container(border=True):
        st.markdown('<div class="panel-header">特征重要性分析</div>', unsafe_allow_html=True)
        feat_df = get_feature_importance()
        if not feat_df.empty:
            top_feat = feat_df.head(10)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=top_feat["feature"], x=top_feat["importance"], orientation="h",
                marker=dict(color=top_feat["importance"], colorscale=[[0, "#3b82f6"], [1, "#06b6d4"]], showscale=False),
                text=[f"{v:.1f}%" for v in top_feat["importance"]], textposition="outside", textfont=dict(color="#cbd5e1", size=11),
                hovertemplate="<b>%{y}</b><br>重要性: %{x:.2f}%<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
                margin=dict(l=140, r=60, t=10, b=20), height=340,
                xaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="重要性 (%)", title_font_color="#cbd5e1"),
                yaxis=dict(showgrid=False, title="", autorange="reversed"), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("暂无特征重要性数据，请先完成模型训练")

with insight_col:
    with st.container(border=True):
        st.markdown('<div class="panel-header">智能洞察</div>', unsafe_allow_html=True)
        insights = []
        if not display_df.empty:
            today_v = display_df["客流量"].iloc[-1]
            if len(display_df) > 7:
                recent = display_df["客流量"].tail(7).mean()
                prev = display_df["客流量"].tail(14).head(7).mean()
                trend_change = (recent - prev) / prev * 100 if prev > 0 else 0
                if trend_change > 10:
                    insights.append(("🚀 短期趋势上升", f"近7日日均客流 {recent:,.0f} 人次，较上周增长 {trend_change:.1f}%，建议增加运营人员配置。", "warning"))
                elif trend_change < -10:
                    insights.append(("📉 短期趋势下降", f"近7日日均客流 {recent:,.0f} 人次，较上周下降 {abs(trend_change):.1f}%，建议检查是否有特殊事件影响。", "danger"))
                else:
                    insights.append(("➖ 客流平稳", f"近7日日均客流 {recent:,.0f} 人次，与上周基本持平，运营状况稳定。", "normal"))
            if not forecast_df.empty:
                max_pred = forecast_df["预测"].max()
                max_pred_date = forecast_df.loc[forecast_df["预测"].idxmax(), "日期"]
                if max_pred > CAPACITY * PEAK_RATIO:
                    insights.append(("🔴 高峰预警", f"预测显示 {max_pred_date} 将达 {max_pred:,.0f} 人次，接近承载上限，建议提前部署限流措施。", "danger"))
            if metrics and metrics.get('r2', 0) > 0.95:
                insights.append(("✅ 模型高准确度", f"XGBoost 模型 R2 = {metrics.get('r2', 0):.4f}，预测准确度极高，可信赖用于运营决策。", "normal"))
            if not display_df.empty and len(display_df) > 30:
                current_month = display_df["日期"].iloc[-1].month
                month_avg = display_df[display_df["日期"].dt.month == current_month]["客流量"].mean()
                overall_avg = display_df["客流量"].mean()
                if month_avg > overall_avg * 1.2:
                    insights.append(("🌊 旺季特征", f"当前处于客流旺季，月均客流 {month_avg:,.0f} 人次，高于全年均值 {overall_avg:,.0f} 人次。", "warning"))
        if not insights:
            insights = [("📊 暂无洞察", "请检查数据源或完成模型训练后查看实时洞察。", "normal")]
        for title, text, level in insights[:4]:
            card_class = "warning" if level == "warning" else "danger" if level == "danger" else ""
            st.markdown(f"""
            <div class="insight-card {card_class}">
                <div class="insight-title">{title}</div>
                <div class="insight-text">{text}</div>
            </div>
            """, unsafe_allow_html=True)

# ========== 历史明细 + 客流分布 ==========
table_col, dist_col = st.columns([6, 4])

with table_col:
    with st.container(border=True):
        st.markdown('<div class="panel-header">历史数据明细</div>', unsafe_allow_html=True)
        if not display_df.empty:
            display_table = display_df.copy()
            display_table["日期"] = display_table["日期"].dt.strftime("%Y-%m-%d")
            display_table["客流量"] = display_table["客流量"].apply(lambda x: f"{x:,.0f}")
            display_table["星期"] = display_df["日期"].dt.day_name().map({
                'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
                'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
            })
            display_table["环比"] = display_df["客流量"].pct_change().apply(lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "—")
            st.dataframe(
                display_table[["日期", "星期", "客流量", "环比"]].tail(14),
                use_container_width=True, hide_index=True, height=320
            )

with dist_col:
    with st.container(border=True):
        st.markdown('<div class="panel-header">客流分布</div>', unsafe_allow_html=True)
        if not display_df.empty:
            display_df["weekday"] = display_df["日期"].dt.dayofweek
            weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
            weekday_avg = display_df.groupby("weekday")["客流量"].mean().reset_index()
            weekday_avg["星期"] = weekday_avg["weekday"].map(weekday_map)
            fig = go.Figure()
            colors = ["#3b82f6" if d < 5 else "#06b6d4" for d in weekday_avg["weekday"]]
            fig.add_trace(go.Bar(
                x=weekday_avg["星期"], y=weekday_avg["客流量"], marker_color=colors,
                text=[f"{v:,.0f}" for v in weekday_avg["客流量"]], textposition="outside", textfont=dict(color="#cbd5e1", size=11),
                hovertemplate="<b>%{x}</b><br>均值: %{y:,.0f} 人次<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
                margin=dict(l=20, r=20, t=10, b=20), height=320,
                xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="日均客流", title_font_color="#cbd5e1"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ========== 关于数据来源与方法论（折叠，精简首屏） ==========
with st.expander("关于数据来源与方法论", expanded=False):
    st.markdown("""
<div style="font-size: 12px; color: #cbd5e1; line-height: 1.6;">
    <strong style="color:#f1f5f9;">为什么用九寨沟数据？</strong> 国内5A级景区中，九寨沟是<strong style="color:#3b82f6;">唯一每日在官网公开精确游客人数</strong>的景区。
    该数据已被多篇 SCI 论文引用做客流预测研究。本项目特征均为通用维度（节假日、天气、历史趋势等），
    方法论可无缝迁移至<strong style="color:#3b82f6;">同类景区</strong>。<br><br>
    <strong style="color:#f1f5f9;">数据来源：</strong>https://www.jiuzhai.com/news/number-of-tourists（九寨沟景区官方网站）
</div>
""", unsafe_allow_html=True)

if auto_refresh:
    _interval = int(refresh_interval.replace("s", ""))
    _time.sleep(_interval)
    st.rerun()
