"""
景区客流预测平台 - 节假日客流分析页
真实节假日数据 × 客流交叉分析：哪个节最旺 · 节前节后效应 · 节假日类型对比
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.navbar import render_navbar, render_sidebar
from utils.holidays import get_holiday_map
from config import DAILY_CSV, HOLIDAY_COVER_UNTIL_YEAR, CAPACITY

render_navbar("节假日分析")
auto_refresh, refresh_interval = render_sidebar()

WEEKDAY_CN = {
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三", "Thursday": "周四",
    "Friday": "周五", "Saturday": "周六", "Sunday": "周日",
}

@st.cache_data(ttl=3600)
def load_daily():
    """加载真实客流主数据；文件缺失时返回带列名的空 DataFrame（触发页面降级提示）"""
    daily_path = DAILY_CSV
    if not os.path.exists(daily_path):
        return pd.DataFrame(columns=["date", "visitors", "holiday_name", "is_holiday"])
    daily = pd.read_csv(daily_path, encoding="utf-8-sig")
    daily["date"] = pd.to_datetime(daily["date"])
    daily["visitors"] = daily["visitors"].astype(float)
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily
    return daily


def load_holiday_data():
    """合并节假日标记到日度客流"""
    daily = load_daily()
    if daily.empty:
        return daily
    holiday_map = get_holiday_map(cover_until_year=HOLIDAY_COVER_UNTIL_YEAR)
    daily["holiday_name"] = daily["date"].dt.strftime("%Y-%m-%d").map(holiday_map)
    daily["is_holiday"] = daily["holiday_name"].notna().astype(int)
    return daily


def build_holiday_segments(hol):
    """将节假日日期按『连续天数 + 同名』切分为独立节假日段"""
    segments = []
    current = []
    for _, row in hol.iterrows():
        if current and (row["date"] - current[-1]["date"]).days == 1 and current[-1]["holiday_name"] == row["holiday_name"]:
            current.append(row)
        else:
            if current:
                segments.append(current)
            current = [row]
    if current:
        segments.append(current)
    return segments


daily = load_holiday_data()
hol = daily[daily["is_holiday"] == 1].copy()
normal = daily[daily["is_holiday"] == 0]

if hol.empty:
    st.warning("未找到节假日数据，请确认 powerbi/holidays_2019_2025.csv 与 data/jiuzhaigou_daily.csv 存在")
    st.stop()

# ========== 1. KPI 概览 ==========
hol_agg = hol.groupby("holiday_name")["visitors"].agg(["mean", "max", "min", "count"]).reset_index()
hol_agg.columns = ["节假日", "日均客流", "峰值客流", "最低客流", "天数"]
hol_agg = hol_agg.sort_values("日均客流", ascending=False).reset_index(drop=True)
busiest = hol_agg.iloc[0]
holiday_days = len(hol)
holiday_share = hol["visitors"].sum() / daily["visitors"].sum() * 100

with st.container(border=True):
    st.markdown('<div class="panel-header">节假日客流概览</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    kpis = [
        ("节假日天数", f"{holiday_days:,} 天", f"{daily['date'].min():%Y-%m} ~ {daily['date'].max():%Y-%m}"),
        ("覆盖节日", f"{hol['holiday_name'].nunique()} 类", "含中秋国庆合并节"),
        ("节假日日均", f"{hol['visitors'].mean():,.0f}", "人次/天"),
        ("客流占比", f"{holiday_share:.1f}%", "节假日客流占总客流"),
        ("最旺节日", f"{busiest['节假日']}", f"日均 {busiest['日均客流']:,.0f} 人次"),
    ]
    for col, (label, value, sub) in zip([c1, c2, c3, c4, c5], kpis):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{value}</div>
                <div class="stat-label">{label}</div>
                <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

# ========== 2. 各节假日客流对比 ==========
col_a, col_b = st.columns([3, 2])

with col_a:
    with st.container(border=True):
        st.markdown('<div class="panel-header">各节假日日均客流对比</div>', unsafe_allow_html=True)
        bar_df = hol_agg.sort_values("日均客流")
        colors = ["#3b82f6" if v < hol_agg["日均客流"].mean() else "#06b6d4" for v in bar_df["日均客流"]]
        fig_bar = go.Figure(go.Bar(
            y=bar_df["节假日"], x=bar_df["日均客流"], orientation="h", marker_color=colors,
            text=[f"{v:,.0f}" for v in bar_df["日均客流"]], textposition="outside",
            textfont=dict(color="#cbd5e1", size=11),
            hovertemplate="<b>%{y}</b><br>日均客流: %{x:,.0f} 人次<extra></extra>",
        ))
        fig_bar.add_vline(x=daily["visitors"].mean(), line_dash="dot", line_color="#f59e0b", line_width=1,
                          annotation_text="全期日均", annotation_font_color="#f59e0b", annotation_font_size=10)
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
            margin=dict(l=20, r=60, t=10, b=20), height=360,
            xaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="日均客流（人次）", title_font_color="#cbd5e1"),
            yaxis=dict(showgrid=False, title=""), showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

with col_b:
    with st.container(border=True):
        st.markdown('<div class="panel-header">节假日 vs 非节假日</div>', unsafe_allow_html=True)
        box_df = pd.DataFrame({
            "类型": ["节假日"] * len(hol) + ["非节假日"] * len(normal),
            "客流量": list(hol["visitors"]) + list(normal["visitors"]),
        })
        fig_box = go.Figure()
        for idx, (label, color) in enumerate([("非节假日", "#3b82f6"), ("节假日", "#06b6d4")]):
            sub = box_df[box_df["类型"] == label]["客流量"]
            fig_box.add_trace(go.Box(
                y=sub, name=label, marker_color=color, boxmean="sd", width=0.4,
                hovertemplate="<b>%{y:,.0f}</b><extra>" + label + "</extra>",
            ))
        fig_box.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
            margin=dict(l=20, r=20, t=10, b=20), height=360,
            yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="客流量（人次）", title_font_color="#cbd5e1"),
            xaxis=dict(showgrid=False, title=""), showlegend=False,
        )
        st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})

# ========== 3. 节前节后效应 ==========
with st.container(border=True):
    st.markdown('<div class="panel-header">节前节后效应（节假日前后 7 天客流均值）</div>', unsafe_allow_html=True)
    segments = build_holiday_segments(hol)
    visitors_by_date = dict(zip(daily["date"], daily["visitors"]))
    offset_data = {}
    for seg in segments:
        start = seg[0]["date"]
        for off in range(-7, 8):
            d = start + timedelta(days=off)
            if d in visitors_by_date:
                offset_data.setdefault(off, []).append(visitors_by_date[d])

    if offset_data:
        offset_order = sorted(offset_data.keys())
        offset_mean = [np.mean(offset_data[o]) for o in offset_order]
        offset_df = pd.DataFrame({"offset": offset_order, "日均客流": offset_mean})

        # 标注节中区间（以 7 天长假为参考：offset 0-6 视为节中）
        fig_eff = go.Figure()
        fig_eff.add_trace(go.Scatter(
            x=offset_df["offset"], y=offset_df["日均客流"], mode="lines+markers",
            line=dict(color="#06b6d4", width=2.5), marker=dict(size=7, color="#06b6d4", line=dict(color="white", width=2)),
            hovertemplate="偏移 <b>%{x}</b> 天<br>客流: %{y:,.0f}<extra></extra>",
        ))
        # 节前区间底色
        fig_eff.add_vrect(x0=-7, x1=-0.5, fillcolor="rgba(59,130,246,0.06)", line_width=0, annotation_text="节前", annotation_font_color="#3b82f6")
        fig_eff.add_vrect(x0=0.5, x1=6.5, fillcolor="rgba(6,182,212,0.08)", line_width=0, annotation_text="节中", annotation_font_color="#06b6d4")
        fig_eff.add_vrect(x0=7, x1=7.5, fillcolor="rgba(16,185,129,0.06)", line_width=0, annotation_text="节后", annotation_font_color="#10b981")
        fig_eff.add_hline(y=daily["visitors"].mean(), line_dash="dot", line_color="#f59e0b", line_width=1,
                          annotation_text="全期日均", annotation_font_color="#f59e0b", annotation_font_size=10)
        fig_eff.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
            margin=dict(l=40, r=40, t=30, b=40), height=360,
            xaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="相对节假日首日偏移（天）", title_font_color="#cbd5e1", dtick=1),
            yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="平均客流（人次）", title_font_color="#cbd5e1"),
            showlegend=False, hovermode="x unified",
        )
        st.plotly_chart(fig_eff, use_container_width=True, config={"displayModeBar": False})

        peak_off = offset_df.loc[offset_df["日均客流"].idxmax(), "offset"]
        pre = offset_df.loc[offset_df["offset"].isin([-1, -2, -3]), "日均客流"].mean()
        mid = offset_df.loc[offset_df["offset"].isin([0, 1, 2, 3]), "日均客流"].mean()
        post = offset_df.loc[offset_df["offset"].isin([5, 6, 7]), "日均客流"].mean()
        st.markdown(f"""
        <div style="font-size:12px; color:#cbd5e1; line-height:1.7; margin-top:4px;">
            <strong style="color:#f1f5f9;">解读：</strong>
            客流在节假日首日前 <strong style="color:#3b82f6;">{pre:,.0f}</strong> 人次 → 节中 <strong style="color:#06b6d4;">{mid:,.0f}</strong> 人次 → 节后 <strong style="color:#10b981;">{post:,.0f}</strong> 人次，
            峰值出现在偏移 <strong style="color:#f59e0b;">{peak_off:+d}</strong> 天。节假日是九寨沟客流的核心驱动因素，
            建议在峰值前 <strong style="color:#f59e0b;">3-5 天</strong>启动票务与人员预案。
        </div>
        """, unsafe_allow_html=True)

# ========== 4. 年度 × 节假日热力图 ==========
with st.container(border=True):
    st.markdown('<div class="panel-header">年度 × 节假日 日均客流热力图</div>', unsafe_allow_html=True)
    hol["year"] = hol["date"].dt.year
    pivot = hol.pivot_table(index="year", columns="holiday_name", values="visitors", aggfunc="mean")
    # 按年份升序、按各节日平均值降序排列
    pivot = pivot.sort_index()
    pivot = pivot.reindex(columns=pivot.mean().sort_values(ascending=False).index)

    if not pivot.empty:
        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values, x=[str(c) for c in pivot.columns], y=[str(i) for i in pivot.index],
            colorscale=[[0, "#0f2642"], [0.5, "#1d4ed8"], [1, "#06b6d4"]],
            zmin=pivot.values[~np.isnan(pivot.values)].min() if not np.isnan(pivot.values).all() else 0,
            zmax=pivot.values[~np.isnan(pivot.values)].max() if not np.isnan(pivot.values).all() else 1,
            text=[[f"{v:,.0f}" if not np.isnan(v) else "—" for v in row] for row in pivot.values],
            texttemplate="%{text}", textfont=dict(color="#e2e8f0", size=11),
            hovertemplate="<b>%{y}年 · %{x}</b><br>日均客流: %{z:,.0f}<extra></extra>",
        ))
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=12),
            margin=dict(l=40, r=20, t=20, b=40), height=320,
            xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=False, title="年份", title_font_color="#cbd5e1"),
            showlegend=False,
        )
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
        st.markdown("""
        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">注：空白单元格表示该年份无对应节假日数据（如 2020 年初疫情闭园、部分年份中秋与国庆合并为「中秋国庆」）。</div>
        """, unsafe_allow_html=True)

# ========== 5. 节假日明细表 ==========
with st.container(border=True):
    st.markdown('<div class="panel-header">节假日客流明细</div>', unsafe_allow_html=True)
    detail = hol.copy()
    detail["星期"] = detail["date"].dt.day_name().map(WEEKDAY_CN)
    detail["日期"] = detail["date"].dt.strftime("%Y-%m-%d")
    detail = detail.sort_values("date", ascending=False).reset_index(drop=True)
    detail["承载率"] = (detail["visitors"] / CAPACITY * 100).apply(lambda x: f"{x:.1f}%")
    detail["客流量"] = detail["visitors"].apply(lambda x: f"{x:,.0f}")
    detail = detail.rename(columns={"holiday_name": "节假日"})

    sel_year = st.selectbox("筛选年份", options=["全部"] + sorted(detail["date"].dt.year.unique().tolist(), reverse=True), key="holiday_year")
    show = detail if sel_year == "全部" else detail[detail["date"].dt.year == int(sel_year)]
    st.dataframe(
        show[["日期", "星期", "节假日", "客流量", "承载率"]],
        use_container_width=True, hide_index=True, height=320,
    )
    st.caption(f"共 {len(show):,} 个节假日日期")

if auto_refresh:
    import time as _time
    _interval = int(refresh_interval.replace("s", ""))
    _time.sleep(_interval)
    st.rerun()
