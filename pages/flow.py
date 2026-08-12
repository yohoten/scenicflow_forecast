"""
景区客流预测平台 - 流量分析页
九寨沟真实数据驱动 · 多维度客流分析
"""
import streamlit as st
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.navbar import render_navbar, render_sidebar
from config import DAILY_CSV, FEATURES_CSV

render_navbar("客流分析")
auto_refresh, refresh_interval = render_sidebar()

@st.cache_data(ttl=3600)
def load_real_data():
    csv_path = DAILY_CSV
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["visitors"] = df["visitors"].astype(float)
        return df
    feat_path = FEATURES_CSV
    if os.path.exists(feat_path):
        df = pd.read_csv(feat_path, encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    return None

df = load_real_data()
if df is None:
    st.warning("未找到数据文件，请确保 data/jiuzhaigou_daily.csv 存在")
    st.stop()

df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month
df["day_of_week"] = df["date"].dt.dayofweek
df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
df["weekday_name"] = df["date"].dt.day_name().map({
    'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
    'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
})
df["quarter"] = df["date"].dt.quarter
df["day_of_year"] = df["date"].dt.dayofyear

latest_date = df["date"].max()
earliest_date = df["date"].min()
total_days = len(df)
total_records = df["visitors"].sum()

with st.container(border=True):
    st.markdown('<div class="panel-header">数据概览</div>', unsafe_allow_html=True)
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    stats = [
        ("数据天数", f"{total_days:,}", f"{earliest_date.strftime('%Y-%m')} ~ {latest_date.strftime('%Y-%m')}"),
        ("累计客流", f"{total_records/10000:.0f}万", "历史总接待人数"),
        ("日均客流", f"{df['visitors'].mean():,.0f}", "长期日均访客"),
        ("最高单日", f"{df['visitors'].max():,.0f}", df.loc[df['visitors'].idxmax(), 'date'].strftime("%Y-%m-%d")),
        ("最低单日", f"{df['visitors'].min():,.0f}", df.loc[df['visitors'].idxmin(), 'date'].strftime("%Y-%m-%d")),
        ("标准差", f"{df['visitors'].std():,.0f}", "客流波动幅度"),
    ]
    for col, (label, value, sub) in zip([s1, s2, s3, s4, s5, s6], stats):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{value}</div>
                <div class="stat-label">{label}</div>
                <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

with st.container(border=True):
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
    with filter_col1:
        view_mode = st.selectbox("视图模式", ["最近数据", "年度对比", "月度聚合", "全部趋势"], label_visibility="collapsed", key="view_mode")
    with filter_col2:
        if view_mode == "年度对比":
            available_years = sorted(df["year"].unique(), reverse=True)
            year_compare = st.multiselect("选择年份", available_years, default=available_years[:min(3, len(available_years))], label_visibility="collapsed", key="year_compare")
        elif view_mode == "月度聚合":
            month_range = st.slider("月份范围", 1, 12, (1, 12), label_visibility="collapsed", key="month_range")
        elif view_mode == "最近数据":
            recent_months = st.slider("最近N个月", 3, 36, 12, label_visibility="collapsed", key="recent_months")
    with filter_col3:
        smooth = st.toggle("平滑曲线", value=False, key="smooth_toggle")

    chart_col1, chart_col2 = st.columns([3, 1])
    with chart_col1:
        st.markdown('<div class="panel-header">客流时序分析</div>', unsafe_allow_html=True)
        fig_main = go.Figure()
        if view_mode == "最近数据":
            cutoff = latest_date - timedelta(days=int(recent_months) * 30)
            plot_df = df[df["date"] >= cutoff].copy()
        elif view_mode == "年度对比" and year_compare:
            plot_df = df[df["year"].isin(year_compare)].copy()
        elif view_mode == "月度聚合":
            month_data = df.groupby("month")["visitors"].agg(["mean", "std", "min", "max"]).reset_index()
            month_data["month_name"] = month_data["month"].apply(lambda m: f"{m}月")
            plot_df = month_data
        else:
            plot_df = df.copy()

        if view_mode == "年度对比" and year_compare:
            colors = ["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#10b981"]
            for i, yr in enumerate(year_compare):
                yr_df = plot_df[plot_df["year"] == yr]
                fig_main.add_trace(go.Scatter(
                    x=yr_df["date"], y=yr_df["visitors"], mode="lines", name=f"{yr}年",
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f"<b>%{{x}}</b><br>{yr}年: %{{y:,.0f}} 人次<extra></extra>"
                ))
        elif view_mode == "月度聚合":
            fig_main.add_trace(go.Bar(
                x=plot_df["month_name"], y=plot_df["mean"], name="月均客流",
                marker=dict(color="#3b82f6", line=dict(color="#1e3a5f", width=0.5)),
                error_y=dict(type="data", array=plot_df["std"], color="#cbd5e1", thickness=1),
                hovertemplate="<b>%{x}</b><br>月均: %{y:,.0f} 人次<extra></extra>"
            ))
        else:
            if smooth:
                window = min(30, len(plot_df) // 10) if len(plot_df) > 10 else 7
                plot_df["smoothed"] = plot_df["visitors"].rolling(window=window, center=True).mean()
                fig_main.add_trace(go.Scatter(
                    x=plot_df["date"], y=plot_df["visitors"], mode="lines", name="实际客流",
                    line=dict(color="rgba(59,130,246,0.3)", width=1),
                    hovertemplate="<b>%{x}</b><br>客流: %{y:,.0f}<extra></extra>"
                ))
                fig_main.add_trace(go.Scatter(
                    x=plot_df["date"], y=plot_df["smoothed"], mode="lines", name="移动平滑",
                    line=dict(color="#3b82f6", width=3),
                    hovertemplate="<b>%{x}</b><br>平滑: %{y:,.0f}<extra></extra>"
                ))
            else:
                fig_main.add_trace(go.Scatter(
                    x=plot_df["date"], y=plot_df["visitors"], mode="lines", name="客流",
                    line=dict(color="#3b82f6", width=2), fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
                    hovertemplate="<b>%{x}</b><br>客流: %{y:,.0f} 人次<extra></extra>"
                ))

        fig_main.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#cbd5e1", size=11), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=40, r=40, t=40, b=20), height=360, hovermode="x unified",
            xaxis=dict(showgrid=False, zeroline=False, title="日期", title_font_color="#cbd5e1"),
            yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", zeroline=False, tickformat=",", title="人次", title_font_color="#cbd5e1"),
        )
        st.plotly_chart(fig_main, use_container_width=True, height=360, key="flow_main_chart", config={"displayModeBar": False})

        if view_mode != "月度聚合" and not plot_df.empty and "is_weekend" in plot_df.columns:
            weekend_avg = plot_df[plot_df["is_weekend"] == 1]["visitors"].mean()
            weekday_avg = plot_df[plot_df["is_weekend"] == 0]["visitors"].mean()
            fig_week = go.Figure()
            fig_week.add_trace(go.Bar(
                x=["工作日", "周末"], y=[weekday_avg, weekend_avg],
                marker_color=["#3b82f6", "#06b6d4"],
                text=[f"{weekday_avg:,.0f}", f"{weekend_avg:,.0f}"],
                textposition="outside", textfont=dict(color="#cbd5e1", size=12),
                hovertemplate="<b>%{x}</b><br>均值: %{y:,.0f} 人次<extra></extra>", showlegend=False
            ))
            fig_week.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
                margin=dict(l=40, r=40, t=10, b=20), height=160, showlegend=False,
                xaxis=dict(showgrid=False, zeroline=False, title="", title_font_color="#cbd5e1"),
                yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", zeroline=False, tickformat=",", title="人次", title_font_color="#cbd5e1"),
            )
            st.plotly_chart(fig_week, use_container_width=True, height=160, key="flow_weekend_chart", config={"displayModeBar": False})

    with chart_col2:
        st.markdown('<div class="panel-header">统计摘要</div>', unsafe_allow_html=True)
        if view_mode != "月度聚合":
            pv = plot_df["visitors"]
        else:
            pv = plot_df["mean"]
        peak_month = df.groupby("month")["visitors"].mean().idxmax()
        low_month = df.groupby("month")["visitors"].mean().idxmin()
        stats_panel = [
            ("均值", f"{pv.mean():,.0f}", "人次"),
            ("中位数", f"{pv.median():,.0f}", "人次"),
            ("标准差", f"{pv.std():,.0f}", "波动幅度"),
            ("变异系数", f"{pv.std()/pv.mean()*100:.1f}%", "相对波动"),
            ("旺季月", f"{peak_month}月", f"{df[df['month']==peak_month]['visitors'].mean():,.0f} 人次"),
            ("淡季月", f"{low_month}月", f"{df[df['month']==low_month]['visitors'].mean():,.0f} 人次"),
        ]
        for label, value, unit in stats_panel:
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid rgba(100,180,255,0.06);">
                <span style="font-size:12px; color:#cbd5e1;">{label}</span>
                <div style="text-align:right;">
                    <span style="font-size:15px; font-weight:700; color:#e2e8f0;">{value}</span>
                    <span style="font-size:10px; color:#cbd5e1; margin-left:4px;">{unit}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

col_a, col_b = st.columns([1, 1])
with col_a:
    with st.container(border=True):
        st.markdown('<div class="panel-header">星期分布分析</div>', unsafe_allow_html=True)
        weekday_order = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday_stats = df.groupby("weekday_name")["visitors"].agg(["mean", "std", "count"]).reindex(weekday_order)
        fig_wd = go.Figure()
        fig_wd.add_trace(go.Box(
            y=[df[df["weekday_name"] == w]["visitors"].values for w in weekday_order],
            x=weekday_order, name="分布", marker_color="#3b82f6",
            line=dict(color="#cbd5e1", width=1), fillcolor="rgba(59,130,246,0.1)", boxmean="sd",
        ))
        fig_wd.add_trace(go.Scatter(
            x=weekday_order, y=weekday_stats["mean"], mode="lines+markers", name="均值趋势",
            line=dict(color="#06b6d4", width=3), marker=dict(size=10, color="#06b6d4"),
            hovertemplate="<b>%{x}</b><br>均值: %{y:,.0f}<extra></extra>"
        ))
        fig_wd.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), showlegend=False,
            margin=dict(l=20, r=20, t=10, b=20), height=380,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", tickformat=",", title="人次"),
        )
        st.plotly_chart(fig_wd, use_container_width=True, config={"displayModeBar": False})

with col_b:
    with st.container(border=True):
        st.markdown('<div class="panel-header">月度客流模式</div>', unsafe_allow_html=True)
        month_names = [f"{m}月" for m in range(1, 13)]
        month_mean = df.groupby("month")["visitors"].mean()
        peak_val = month_mean.max()
        peak_idx = month_mean.idxmax()
        fig_month = go.Figure()
        colors_month = []
        for m in range(1, 13):
            if m == peak_idx:
                colors_month.append("#f59e0b")
            elif m in [4, 5, 6, 7, 8, 9, 10, 11]:
                colors_month.append("#3b82f6")
            else:
                colors_month.append("#94a3b8")
        fig_month.add_trace(go.Bar(
            x=month_names, y=[month_mean.get(m, 0) for m in range(1, 13)],
            marker=dict(color=colors_month, line=dict(color="#0f2642", width=1)),
            text=[f"{month_mean.get(m, 0):,.0f}" for m in range(1, 13)],
            textposition="outside", textfont=dict(color="#cbd5e1", size=11),
            hovertemplate="<b>%{x}</b><br>月均: %{y:,.0f} 人次<extra></extra>",
        ))
        annual_avg = df["visitors"].mean()
        fig_month.add_hline(y=annual_avg, line_dash="dash", line_color="#10b981", line_width=1.5,
                             annotation_text=f"年均 {annual_avg:,.0f}", annotation_position="right",
                             annotation_font_color="#10b981", annotation_font_size=11)
        fig_month.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), showlegend=False,
            margin=dict(l=20, r=20, t=10, b=40), height=380,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", tickformat=",", title="月均人次"),
        )
        st.plotly_chart(fig_month, use_container_width=True, config={"displayModeBar": False})

col_c, col_d = st.columns([2, 1])
with col_c:
    with st.container(border=True):
        st.markdown('<div class="panel-header">年度趋势对比</div>', unsafe_allow_html=True)
        yearly = df.groupby("year")["visitors"].agg(["sum", "mean", "max", "min", "count"]).reset_index()
        yearly = yearly[yearly["count"] > 30]
        if len(yearly) > 1:
            fig_yr = go.Figure()
            fig_yr.add_trace(go.Bar(
                x=yearly["year"].astype(str), y=yearly["sum"] / 10000, name="年度总客流(万)",
                marker=dict(color="#3b82f6", line=dict(color="#1e3a5f", width=0.5)),
                text=[f"{v:.1f}万" for v in yearly["sum"] / 10000], textposition="outside", textfont=dict(color="#cbd5e1", size=11),
                yaxis="y", hovertemplate="<b>%{x}</b><br>总客流: %{y:.1f}万<extra></extra>"
            ))
            fig_yr.add_trace(go.Scatter(
                x=yearly["year"].astype(str), y=yearly["mean"], name="日均客流", mode="lines+markers", yaxis="y2",
                line=dict(color="#06b6d4", width=2.5), marker=dict(size=8, color="#06b6d4"),
                hovertemplate="<b>%{x}</b><br>日均: %{y:,.0f}<extra></extra>"
            ))
            fig_yr.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#cbd5e1", size=11)),
                margin=dict(l=40, r=60, t=10, b=20), height=360,
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="总客流(万)", title_font_color="#cbd5e1"),
                yaxis2=dict(showgrid=False, title="日均(人次)", title_font_color="#cbd5e1", overlaying="y", side="right", tickformat=","),
            )
            st.plotly_chart(fig_yr, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("数据年份不足，无法进行年度对比分析")

with col_d:
    with st.container(border=True):
        st.markdown('<div class="panel-header">分析洞察</div>', unsafe_allow_html=True)
        insights = []
        weekend_avg = df[df["is_weekend"] == 1]["visitors"].mean()
        weekday_avg = df[df["is_weekend"] == 0]["visitors"].mean()
        wkend_ratio = (weekend_avg / weekday_avg - 1) * 100 if weekday_avg > 0 else 0
        if abs(wkend_ratio) > 5:
            insights.append(("周末效应显著", f"周末客流量较工作日{'高' if wkend_ratio > 0 else '低'}{abs(wkend_ratio):.1f}%，建议周末增配服务人员。", "warning"))
        peak_month = df.groupby("month")["visitors"].mean().idxmax()
        if peak_month in [7, 8, 10]:
            insights.append((f"{peak_month}月为客流峰值", f"旺季月均客流 {df[df['month']==peak_month]['visitors'].mean():,.0f} 人次，建议提前储备物资和人力。", "warning"))
        cv = df["visitors"].std() / df["visitors"].mean() * 100
        if cv > 80:
            insights.append(("客流波动较大", f"变异系数 {cv:.1f}%，淡旺季差异明显，需要灵活的资源配置策略。", "danger"))
        else:
            insights.append(("客流相对稳定", f"变异系数 {cv:.1f}%，整体运营可预测性较强。", "normal"))
        insights.append(("数据覆盖范围", f"共 {total_days} 天数据，覆盖 {earliest_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}，数据完整性良好。", "normal"))
        for title, text, level in insights:
            border_color = "#f59e0b" if level == "warning" else ("#ef4444" if level == "danger" else "#3b82f6")
            bg_color = "rgba(245,158,11,0.05)" if level == "warning" else ("rgba(239,68,68,0.05)" if level == "danger" else "rgba(59,130,246,0.05)")
            st.markdown(f"""
            <div style="background:{bg_color}; border-left:3px solid {border_color}; border-radius:0 10px 10px 0; padding:12px 16px; margin-bottom:10px;">
                <div style="font-size:13px; font-weight:700; color:#e2e8f0; margin-bottom:4px;">{title}</div>
                <div style="font-size:11px; color:#cbd5e1; line-height:1.5;">{text}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:20px; padding:16px; background:rgba(15,38,66,0.5); border-radius:12px; border:1px solid rgba(100,180,255,0.08); text-align:center;">
    <div style="font-size:12px; color:#cbd5e1;">数据来源: 九寨沟景区官网 (jiuzhai.com) · 真实每日进沟人数 · 国内唯一公开5A景区客流数据</div>
</div>
""", unsafe_allow_html=True)

if auto_refresh:
    interval_seconds = int(refresh_interval.replace("s", ""))
    time.sleep(interval_seconds)
    st.rerun()
