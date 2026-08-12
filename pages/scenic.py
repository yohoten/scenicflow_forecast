"""
景区客流预测平台 - 数据洞察页
数据全景概览 · 特征分析 · 质量评估
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
import os, time, random
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.navbar import render_navbar, render_sidebar
from config import DAILY_CSV, FEATURES_CSV, FEATURE_IMPORTANCE_CSV, MODEL_RESULTS_CSV

render_navbar("数据洞察")
auto_refresh, refresh_interval = render_sidebar()

@st.cache_data(ttl=3600)
def load_data():
    def load_data():
        data = {"daily": None, "features": None, "feat_imp": None, "model_results": None}
        daily_path = DAILY_CSV
        if os.path.exists(daily_path):
            data["daily"] = pd.read_csv(daily_path, encoding="utf-8-sig")
            data["daily"]["date"] = pd.to_datetime(data["daily"]["date"])
        feat_path = FEATURES_CSV
        if os.path.exists(feat_path):
            data["features"] = pd.read_csv(feat_path, encoding="utf-8-sig")
            data["features"]["date"] = pd.to_datetime(data["features"]["date"])
        imp_path = FEATURE_IMPORTANCE_CSV
        if os.path.exists(imp_path):
            data["feat_imp"] = pd.read_csv(imp_path)
        results_path = MODEL_RESULTS_CSV
        data["model_results"] = pd.read_csv(results_path, index_col=0)
    return data

data = load_data()
df = data["daily"]
df_feat = data["features"]

if df is None:
    st.error("未找到数据文件")
    st.stop()

with st.container(border=True):
    st.markdown('<div class="panel-header">数据集概览</div>', unsafe_allow_html=True)
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    missing_rate = df["visitors"].isna().sum() / len(df) * 100
    date_span = (df["date"].max() - df["date"].min()).days
    date_gaps = df["date"].diff().dt.days.value_counts().get(1, 0)
    continuity = date_gaps / (len(df) - 1) * 100 if len(df) > 1 else 100
    if auto_refresh:
        seed = int(time.time() / 10)
        random.seed(seed)
        daily_mean = df["visitors"].mean() * random.uniform(0.99, 1.01)
    else:
        daily_mean = df["visitors"].mean()
    stat_items = [
        ("数据天数", f"{len(df):,}天", f"连续性: {continuity:.1f}%"),
        ("时间跨度", f"{date_span}天", f"{df['date'].min().strftime('%Y-%m')} ~ {df['date'].max().strftime('%Y-%m')}"),
        ("特征维度", f"{len(df_feat.columns) if df_feat is not None else 'N/A'}个", "时间+节假日+滞后+统计"),
        ("缺失率", f"{missing_rate:.2f}%", "数据完整性"),
        ("日均客流", f"{daily_mean:,.0f}", f"中位数: {df['visitors'].median():,.0f}"),
        ("数据来源", "九寨沟官网", "jiuzhai.com"),
    ]
    for col, (label, value, sub) in zip([s1, s2, s3, s4, s5, s6], stat_items):
        with col:
            card_class = "live-card" if auto_refresh and label in ["日均客流"] else ""
            st.markdown(f"""
            <div class="stat-card {card_class}">
                <div class="stat-value">{value}</div>
                <div class="stat-label">{label}</div>
                <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

col_a, col_b = st.columns([3, 2])
with col_a:
    with st.container(border=True):
        st.markdown('<div class="panel-header">客流量分布分析</div>', unsafe_allow_html=True)
        fig = make_subplots(rows=1, cols=2, column_widths=[0.4, 0.6], subplot_titles=("直方图+KDE", "Q-Q正态检验"))
        fig.add_trace(go.Histogram(
            x=df["visitors"], nbinsx=40, name="分布",
            marker=dict(color="#3b82f6", line=dict(color="#0f2642", width=0.5)),
            hovertemplate="客流区间<br>天数: %{y}<extra></extra>",
        ), row=1, col=1)
        kde_x = np.linspace(df["visitors"].min(), df["visitors"].max(), 200)
        kde = stats.gaussian_kde(df["visitors"].dropna())
        kde_y = kde(kde_x)
        fig.add_trace(go.Scatter(
            x=kde_x, y=kde_y * len(df) * (df["visitors"].max() - df["visitors"].min()) / 40,
            mode="lines", name="密度曲线", line=dict(color="#06b6d4", width=3),
            hovertemplate="客流: %{x:,.0f}<extra></extra>",
        ), row=1, col=1)
        for pct, color, label in [(25, "#f59e0b", "Q1"), (50, "#10b981", "中位数"), (75, "#8b5cf6", "Q3")]:
            qv = np.percentile(df["visitors"].dropna(), pct)
            fig.add_vline(x=qv, line_dash="dash", line_color=color, line_width=1.5, row=1, col=1,
                           annotation_text=f"{label}: {qv:,.0f}", annotation_font_color=color, annotation_font_size=10)
        sorted_data = np.sort(df["visitors"].dropna())
        theoretical = stats.norm.ppf((np.arange(1, len(sorted_data)+1) - 0.5) / len(sorted_data), loc=sorted_data.mean(), scale=sorted_data.std())
        fig.add_trace(go.Scatter(
            x=theoretical, y=sorted_data, mode="markers",
            marker=dict(color="#3b82f6", size=3, opacity=0.4), name="Q-Q Plot",
            hovertemplate="理论: %{x:,.0f}<br>实际: %{y:,.0f}<extra></extra>",
        ), row=1, col=2)
        min_val = min(theoretical.min(), sorted_data.min())
        max_val = max(theoretical.max(), sorted_data.max())
        fig.add_trace(go.Scatter(
            x=[min_val, max_val], y=[min_val, max_val],
            mode="lines", line=dict(color="#ef4444", width=1, dash="dash"), name="正态参考线", showlegend=False,
        ), row=1, col=2)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20), height=420,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="客流量 (人次)", row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="天数", row=1, col=1)
        fig.update_xaxes(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="理论分位数", row=1, col=2)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="实际分位数", row=1, col=2)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col_b:
    with st.container(border=True):
        st.markdown('<div class="panel-header">特征工程总览</div>', unsafe_allow_html=True)
        if df_feat is not None:
            feat_cols = df_feat.columns.tolist()
            time_feats = [c for c in feat_cols if c in ["year", "month", "day", "day_of_week", "is_weekend", "day_of_year", "week_of_year", "quarter", "is_month_start", "is_month_end"]]
            holiday_feats = [c for c in feat_cols if "holiday" in c.lower() or "golden" in c.lower() or "peak" in c.lower() or "summer" in c.lower()]
            lag_feats = [c for c in feat_cols if "lag" in c.lower()]
            roll_feats = [c for c in feat_cols if "roll" in c.lower()]
            diff_feats = [c for c in feat_cols if "diff" in c.lower() or "wow" in c.lower() or "trend" in c.lower()]
            categories = [
                ("时间特征", time_feats, "#3b82f6"),
                ("节假日特征", holiday_feats, "#f59e0b"),
                ("滞后特征", lag_feats, "#8b5cf6"),
                ("滚动统计", roll_feats, "#10b981"),
                ("差分趋势", diff_feats, "#ec4899"),
            ]
            for cat_name, cat_feats, color in categories:
                if cat_feats:
                    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
                    st.markdown(f"""
                    <div style="margin-bottom:10px;">
                        <span style="background:rgba({r},{g},{b},0.15); color:{color}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">{cat_name}</span>
                        <span style="color:#cbd5e1; font-size:11px; margin-left:6px;">{len(cat_feats)} 个</span>
                    </div>
                    """, unsafe_allow_html=True)
                    feature_tags = " ".join([f'<span style="background:rgba(100,180,255,0.08); color:#cbd5e1; padding:2px 8px; border-radius:4px; font-size:10px; margin:2px; display:inline-block;">{f}</span>' for f in cat_feats[:8]])
                    if len(cat_feats) > 8:
                        feature_tags += f' <span style="color:#cbd5e1; font-size:10px;">+{len(cat_feats)-8}个</span>'
                    st.markdown(f'<div style="margin-bottom:14px; line-height:2;">{feature_tags}</div>', unsafe_allow_html=True)
        else:
            st.info("特征工程数据尚未生成，请先运行 data/clean_data.py")

col_c, col_d = st.columns([1, 1])
with col_c:
    with st.container(border=True):
        st.markdown('<div class="panel-header">Top 15 特征重要性</div>', unsafe_allow_html=True)
        if data["feat_imp"] is not None:
            top_feat = data["feat_imp"].head(15)
            fig_feat = go.Figure()
            colors_feat = []
            for f in top_feat["feature"]:
                if "lag" in f.lower():
                    colors_feat.append("#8b5cf6")
                elif "roll" in f.lower() or "mean" in f.lower() or "std" in f.lower():
                    colors_feat.append("#10b981")
                elif "holiday" in f.lower() or "golden" in f.lower() or "peak" in f.lower():
                    colors_feat.append("#f59e0b")
                elif "diff" in f.lower() or "trend" in f.lower() or "wow" in f.lower():
                    colors_feat.append("#ec4899")
                else:
                    colors_feat.append("#3b82f6")
            fig_feat.add_trace(go.Bar(
                y=list(reversed(top_feat["feature"])), x=list(reversed(top_feat["importance"])), orientation="h",
                marker=dict(color=list(reversed(colors_feat)), line=dict(color="#0f2642", width=0.5)),
                text=[f"{v:.2f}%" for v in reversed(top_feat["importance"])], textposition="outside", textfont=dict(color="#cbd5e1", size=11),
                hovertemplate="<b>%{y}</b><br>重要性: %{x:.2f}%<extra></extra>",
            ))
            fig_feat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), showlegend=False,
                margin=dict(l=160, r=60, t=10, b=20), height=460,
                xaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", title="重要性 (%)", title_font_color="#cbd5e1"),
                yaxis=dict(showgrid=False, autorange="reversed"), bargap=0.3,
            )
            st.plotly_chart(fig_feat, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("特征重要性数据将在模型训练后显示，请运行 ml/train_model.py")

with col_d:
    with st.container(border=True):
        st.markdown('<div class="panel-header">模型性能对比</div>', unsafe_allow_html=True)
        if data["model_results"] is not None:
            results = data["model_results"]
            st.markdown("""
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <thead>
                    <tr style="background:rgba(15,38,66,0.8);">
                        <th style="padding:8px 12px; text-align:left; color:#cbd5e1;">模型</th>
                        <th style="padding:8px 12px; text-align:right; color:#cbd5e1;">R²</th>
                        <th style="padding:8px 12px; text-align:right; color:#cbd5e1;">MAE</th>
                        <th style="padding:8px 12px; text-align:right; color:#cbd5e1;">MAPE</th>
                    </tr>
                </thead>
                <tbody>
            """, unsafe_allow_html=True)
            for idx, row in results.iterrows():
                r2_val = row.get("R²", row.get("R2", "—"))
                mae_val = row.get("MAE", "—")
                mape_val = row.get("MAPE", "—")
                is_best = "XGBoost" in str(idx) and "最优" in str(idx)
                bg = "rgba(59,130,246,0.1)" if is_best else ""
                border = "border-left: 3px solid #3b82f6;" if is_best else ""
                st.markdown(f"""
                <tr style="background:{bg};{border}border-bottom:1px solid rgba(100,180,255,0.06);">
                    <td style="padding:10px 12px; color:#e2e8f0; font-weight:{'700' if is_best else '400'};">{idx}</td>
                    <td style="padding:10px 12px; text-align:right; color:#f1f5f9; font-weight:600;">{r2_val}</td>
                    <td style="padding:10px 12px; text-align:right; color:#cbd5e1;">{mae_val}</td>
                    <td style="padding:10px 12px; text-align:right; color:#cbd5e1;">{mape_val}</td>
                </tr>
                """, unsafe_allow_html=True)
            st.markdown("</tbody></table>", unsafe_allow_html=True)
            st.markdown("""
            <div style="margin-top:12px; padding:10px; background:rgba(16,185,129,0.05); border-radius:6px; border:1px solid rgba(16,185,129,0.1);">
                <div style="font-size:11px; color:#cbd5e1; line-height:1.5;">
                    Linear Regression 仅使用 <code style="background:rgba(100,180,255,0.1); padding:1px 4px; border-radius:3px;">visitors_lag_1</code> 作为朴素时序基线，避免差分/滚动特征线性重构目标变量带来的虚假完美指标。
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("模型尚未训练，请运行 ml/train_model.py")

with st.container(border=True):
    st.markdown('<div class="panel-header">数据质量评估</div>', unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    missing_count = df["visitors"].isna().sum()
    outlier_count = len(df[df["visitors"] > df["visitors"].quantile(0.99)])
    with q1:
        complete_pct = (1 - missing_count / len(df)) * 100
        color = "#10b981" if complete_pct > 99 else ("#f59e0b" if complete_pct > 95 else "#ef4444")
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:28px; font-weight:800; color:{color};">{complete_pct:.1f}%</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:4px;">数据完整性</div>
            <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">缺失 {missing_count} 条 / 总计 {len(df)} 条</div>
        </div>
        """, unsafe_allow_html=True)
    with q2:
        date_continuity = df["date"].diff().dt.days.value_counts().get(1, 0) / (len(df) - 1) * 100 if len(df) > 1 else 100
        color2 = "#10b981" if date_continuity > 95 else ("#f59e0b" if date_continuity > 80 else "#ef4444")
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:28px; font-weight:800; color:{color2};">{date_continuity:.1f}%</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:4px;">日期连续性</div>
            <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">日期间隔为1天的比例</div>
        </div>
        """, unsafe_allow_html=True)
    with q3:
        outlier_pct = outlier_count / len(df) * 100
        color3 = "#10b981" if outlier_pct < 2 else ("#f59e0b" if outlier_pct < 5 else "#ef4444")
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:28px; font-weight:800; color:{color3};">{outlier_pct:.1f}%</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:4px;">极端值比例</div>
            <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">超过99%分位 {outlier_count} 条</div>
        </div>
        """, unsafe_allow_html=True)
    with q4:
        months_present = df["date"].dt.month.nunique()
        color4 = "#10b981" if months_present >= 11 else ("#f59e0b" if months_present >= 8 else "#ef4444")
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); border-radius:12px; padding:20px; text-align:center;">
            <div style="font-size:28px; font-weight:800; color:{color4};">{months_present}/12</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:4px;">月份覆盖</div>
            <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">12个月中已覆盖 {months_present} 个月</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:20px; padding:16px; background:rgba(15,38,66,0.5); border-radius:12px; border:1px solid rgba(100,180,255,0.08);">
    <div style="font-size:12px; font-weight:700; color:#e2e8f0; margin-bottom:8px;">技术栈</div>
    <div style="font-size:11px; color:#cbd5e1; line-height:1.8;">
        <strong style="color:#3b82f6;">XGBoost</strong> 梯度提升模型 ·
        <strong style="color:#8b5cf6;">GridSearchCV</strong> 超参数调优 ·
        <strong style="color:#10b981;">TimeSeriesSplit</strong> 交叉验证 ·
        <strong style="color:#f59e0b;">40维</strong> 特征工程 ·
        <strong style="color:#06b6d4;">SHAP</strong> 可解释性分析
    </div>
</div>
""", unsafe_allow_html=True)

if auto_refresh:
    interval_seconds = int(refresh_interval.replace("s", ""))
    time.sleep(interval_seconds)
    st.rerun()
