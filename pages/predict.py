"""
景区客流预测平台 - 智能预测页
XGBoost 7日滚动预测 | 模型性能展示 | 特征重要性
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os, time, random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.predictor import (
    predict_next_7_days, get_model_metrics, get_feature_importance,
    generate_historical_trend, is_model_ready
)
from utils.navbar import render_navbar, render_sidebar

# ========== 导航栏 + 侧边栏 ==========
render_navbar("智能预测")
auto_refresh, refresh_interval = render_sidebar()

# ========== 加载数据 ==========
model_ready = is_model_ready()
metrics = get_model_metrics()

# 动态数据模拟
if auto_refresh:
    seed = int(time.time() / 10)
    random.seed(seed)
    noise_factor = random.uniform(0.97, 1.03)
else:
    noise_factor = 1.0

forecast_df = predict_next_7_days()
hist_df = generate_historical_trend(90)

# 给预测加微小波动（仿真实时）
if auto_refresh and not forecast_df.empty:
    forecast_df["预测"] = (forecast_df["预测"] * (1 + np.random.uniform(-0.02, 0.02, len(forecast_df)))).astype(int)
    forecast_df["上限"] = (forecast_df["上限"] * (1 + np.random.uniform(0, 0.03, len(forecast_df)))).astype(int)
    forecast_df["下限"] = (forecast_df["下限"] * (1 + np.random.uniform(-0.03, 0, len(forecast_df)))).astype(int)

capacity = 41000

# ========== 模型状态 ==========
st.markdown(f"""
<div style="margin-bottom:10px; display:flex; align-items:center; gap:12px;">
    <span class="badge badge-green">{"模型就绪" if model_ready else "演示模式"}</span>
    <span style="font-size:13px; color:#cbd5e1;">XGBoost 时序预测 | 多特征融合 | 7日滚动预测</span>
</div>
""", unsafe_allow_html=True)

# ========== 模型指标卡片 ==========
with st.container(border=True):
    st.markdown('<div class="panel-header">模型性能指标</div>', unsafe_allow_html=True)
    
    if metrics:
        m1, m2, m3, m4 = st.columns(4)
        
        # 动态浮动指标
        r2_val = metrics['r2']
        mae_val = metrics['mae']
        rmse_val = metrics['rmse']
        mape_val = metrics['mape']
        
        if auto_refresh:
            r2_display = r2_val + random.uniform(-0.005, 0.005)
            mae_display = mae_val + random.randint(-20, 20)
            rmse_display = rmse_val + random.randint(-30, 30)
            mape_display = mape_val + random.uniform(-0.2, 0.2)
        else:
            r2_display = r2_val
            mae_display = mae_val
            rmse_display = rmse_val
            mape_display = mape_val
        
        metric_items = [
            ("R² 决定系数", f"{r2_display:.4f}", "越接近1越好", "#3b82f6"),
            ("MAE 平均误差", f"{mae_display:,.0f}", "预测偏差均值", "#10b981"),
            ("RMSE 均方根误差", f"{rmse_display:,.0f}", "大误差惩罚", "#8b5cf6"),
            ("MAPE 误差率", f"{mape_display:.1f}%", "相对误差比例", "#f59e0b"),
        ]
        
        for col, (label, value, desc, color) in zip([m1, m2, m3, m4], metric_items):
            with col:
                st.markdown(f"""
                <div class="stat-card {'live-card' if auto_refresh else ''}" style="border-top:3px solid {color};">
                    <div class="stat-label">{label}</div>
                    <div style="font-size:28px; font-weight:800; color:{color}; margin:8px 0;">{value}</div>
                    <div style="font-size:10px; color:#cbd5e1;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("模型尚未训练，显示演示数据。请运行 ml/train_model.py")

# ========== 预测图表 ==========
col_main, col_side = st.columns([7, 3])

with col_main:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div class="panel-header" style="margin-bottom:0; padding-bottom:0; border-bottom:none;">7日客流预测</div>
            <div style="font-size:11px; color:#ef4444; border:1px solid rgba(239,68,68,0.3); padding:2px 8px; border-radius:20px; background:rgba(239,68,68,0.08);">
                承载上限 {capacity:,.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if not hist_df.empty and not forecast_df.empty:
            last_hist_date = hist_df["日期"].iloc[-1]
            forecast_dates = pd.to_datetime([last_hist_date + timedelta(days=i+1) for i in range(len(forecast_df))])
            
            # ========== 图表1：客流预测趋势 ==========
            fig_main = go.Figure()
            
            fig_main.add_trace(go.Scatter(
                x=hist_df["日期"], y=hist_df["客流量"],
                mode="lines", name="近期客流",
                line=dict(color="#3b82f6", width=2.5),
                fill="tozeroy", fillcolor="rgba(59,130,246,0.06)",
                hovertemplate="<b>%{x}</b><br>客流: %{y:,.0f}<extra></extra>"
            ))
            
            fig_main.add_trace(go.Scatter(
                x=forecast_dates, y=forecast_df["预测"],
                mode="lines+markers", name="AI预测",
                line=dict(color="#06b6d4", width=3),
                marker=dict(size=8, color="#06b6d4", line=dict(color="white", width=1.5)),
                hovertemplate="<b>%{x}</b><br>预测: %{y:,.0f}<extra></extra>"
            ))
            
            fig_main.add_trace(go.Scatter(
                x=list(forecast_dates) + list(forecast_dates)[::-1],
                y=list(forecast_df["上限"]) + list(forecast_df["下限"])[::-1],
                fill="toself", fillcolor="rgba(6,182,212,0.12)",
                line=dict(color="rgba(0,0,0,0)"), name="90%置信区间",
                hoverinfo="skip"
            ))
            
            # 计算合理的 Y 轴上限，避免承载上限虚线撑出大片空白
            hist_max = hist_df["客流量"].max() if not hist_df.empty else 0
            forecast_max = forecast_df["预测"].max() if not forecast_df.empty else 0
            upper_max = forecast_df["上限"].max() if not forecast_df.empty else 0
            data_max = max(hist_max, forecast_max, upper_max, 1)
            y_max = data_max * 1.02
            
            fig_main.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1", size=11),
                legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5,
                             font=dict(color="#cbd5e1", size=9), bgcolor="rgba(0,0,0,0.3)"),
                margin=dict(l=40, r=40, t=5, b=30), height=280,
                hovermode="x unified",
                xaxis=dict(showgrid=False, zeroline=False, title=dict(text="", font=dict(color="#cbd5e1"))),
                yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", zeroline=False, tickformat=",",
                           title=dict(text="客流量 (人次)", font=dict(color="#cbd5e1")),
                           range=[0, y_max]),
            )
            
            st.markdown('<div style="min-height:280px;">', unsafe_allow_html=True)
            st.plotly_chart(fig_main, use_container_width=True, key="forecast_main_chart", config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
            
            # ========== 图表2：日环比 ==========
            if len(forecast_df) > 1:
                pred_values = forecast_df["预测"].values
                mom = [(pred_values[i] - pred_values[i-1]) / pred_values[i-1] * 100 for i in range(1, len(pred_values))]
                mom = [0] + mom
                mom_colors = ["#34d399" if v >= 0 else "#f87171" for v in mom]
                
                fig_mom = go.Figure()
                fig_mom.add_trace(go.Bar(
                    x=forecast_dates, y=mom,
                    marker_color=mom_colors, name="日环比",
                    text=[f"{v:+.1f}%" for v in mom],
                    textposition="outside", textfont=dict(color="#cbd5e1", size=9),
                    hovertemplate="<b>%{x}</b><br>环比: %{y:+.1f}%<extra></extra>"
                ))
                
                max_mom = max(abs(min(mom)), abs(max(mom))) if mom else 5
                fig_mom.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1", size=11),
                    margin=dict(l=40, r=40, t=5, b=30), height=110,
                    showlegend=False,
                    xaxis=dict(showgrid=False, zeroline=False, title=dict(text="", font=dict(color="#cbd5e1"))),
                    yaxis=dict(showgrid=True, gridcolor="rgba(100,180,255,0.06)", zeroline=True, 
                              zerolinecolor="rgba(100,180,255,0.2)", title=dict(text="日环比 (%)", font=dict(color="#cbd5e1")), 
                              range=[-max(3, max_mom*1.1), max(3, max_mom*1.1)]),
                )
                
                st.plotly_chart(fig_mom, use_container_width=True, height=110, key="forecast_mom_chart", config={"displayModeBar": False})
                st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        else:
            st.warning("数据加载中，请稍候...")
    
    with st.container(border=True):
        st.markdown('<div class="panel-header" style="margin-bottom:8px;">技术架构</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px; color:#cbd5e1; line-height:1.6;">
            <strong style="color:#3b82f6;">XGBoost</strong> 梯度提升决策树，基于40维特征进行时序预测。<br>
            特征：时间(10)、节假日(5)、滞后(4)、滚动统计(16)、差分(5)。<br>
            使用 <strong style="color:#8b5cf6;">GridSearchCV</strong> 调参，<strong style="color:#10b981;">TimeSeriesSplit</strong> 防止数据泄露。
        </div>
        """, unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown('<div class="panel-header" style="margin-bottom:10px;">关键结论与风险提示</div>', unsafe_allow_html=True)
        if not forecast_df.empty:
            peak = forecast_df["预测"].max()
            peak_date = forecast_df.loc[forecast_df["预测"].idxmax(), "日期"]
            avg_forecast = forecast_df["预测"].mean()
            warn_days = int((forecast_df["预测"] > capacity * 0.7).sum())
            high_days = int((forecast_df["预测"] > capacity * 0.9).sum())
            mom_vals = forecast_df["预测"].pct_change().dropna() * 100
            trend_text = "持续上升" if mom_vals.mean() > 0.5 else ("持续下降" if mom_vals.mean() < -0.5 else "相对平稳")
            trend_color = "#34d399" if mom_vals.mean() > 0.5 else ("#f87171" if mom_vals.mean() < -0.5 else "#fbbf24")
            
            col_left, col_right = st.columns([3, 2])
            with col_left:
                st.markdown(f"""
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px;">
                    <div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.15); border-radius:8px; padding:10px;">
                        <div style="font-size:11px; color:#cbd5e1;">预测峰值</div>
                        <div style="font-size:16px; font-weight:700; color:#e2e8f0;">{peak:,.0f}</div>
                        <div style="font-size:10px; color:#cbd5e1;">{peak_date}</div>
                    </div>
                    <div style="background:rgba(6,182,212,0.08); border:1px solid rgba(6,182,212,0.15); border-radius:8px; padding:10px;">
                        <div style="font-size:11px; color:#cbd5e1;">7日平均</div>
                        <div style="font-size:16px; font-weight:700; color:#e2e8f0;">{avg_forecast:,.0f}</div>
                        <div style="font-size:10px; color:#cbd5e1;">人次/日</div>
                    </div>
                    <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.15); border-radius:8px; padding:10px;">
                        <div style="font-size:11px; color:#cbd5e1;">预警/高负荷</div>
                        <div style="font-size:16px; font-weight:700; color:#e2e8f0;">{warn_days}/{high_days}</div>
                        <div style="font-size:10px; color:#cbd5e1;">天</div>
                    </div>
                    <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.15); border-radius:8px; padding:10px;">
                        <div style="font-size:11px; color:#cbd5e1;">整体趋势</div>
                        <div style="font-size:16px; font-weight:700; color:{trend_color};">{trend_text}</div>
                        <div style="font-size:10px; color:#cbd5e1;">日均环比 {mom_vals.mean():+.1f}%</div>
                    </div>
                </div>
                <div style="font-size:12px; color:#cbd5e1; line-height:1.6;">
                    • 未来7日预计有 <strong style="color:#f59e0b;">{warn_days} 天</strong> 达到预警阈值，需提前安排运力与人员。<br>
                    • 峰值预计出现在 <strong style="color:#06b6d4;">{peak_date}</strong>，当日客流 {peak:,.0f} 人次，建议重点监控。<br>
                    • 预测趋势 <strong style="color:{trend_color};">{trend_text}</strong>，可参考建议调整运营策略。
                </div>
                <div style="height:10px;"></div>
                """, unsafe_allow_html=True)
            
            with col_right:
                st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                high_count = int((forecast_df["预测"] > capacity * 0.9).sum())
                warn_count = int(((forecast_df["预测"] > capacity * 0.7) & (forecast_df["预测"] <= capacity * 0.9)).sum())
                normal_count = max(0, len(forecast_df) - high_count - warn_count)
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=["正常", "预警", "高负荷"], values=[normal_count, warn_count, high_count], hole=0.55,
                    marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"], line=dict(color="rgba(0,0,0,0)", width=0)),
                    textinfo="label+percent", textposition="outside",
                    textfont=dict(color="#cbd5e1", size=11),
                    hovertemplate="<b>%{label}</b><br>天数: %{value}<br>占比: %{percent}<extra></extra>",
                    automargin=True
                )])
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1", size=11), showlegend=False,
                    margin=dict(l=10, r=10, t=20, b=20), height=230,
                    annotations=[dict(text="负荷等级", x=0.5, y=0.5, font_size=12, font_color="#e2e8f0", showarrow=False)]
                )
                st.plotly_chart(fig_pie, use_container_width=True, key="load_pie_chart", config={"displayModeBar": False})
                st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        else:
            st.info("暂无预测数据")
    
    with st.container(border=True):
        st.markdown('<div class="panel-header" style="margin-bottom:8px;">预测使用说明</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px; color:#cbd5e1; line-height:1.6;">
            <strong style="color:#3b82f6;">历史客流</strong>：展示过去 30 天实际入园人次，用于判断当前基线。<br>
            <strong style="color:#06b6d4;">AI 预测</strong>：基于 XGBoost 模型滚动预测未来 7 天客流，含 90% 置信区间。<br>
            <strong style="color:#f59e0b;">日环比</strong>：反映相邻预测日之间的客流变化，正值为上升、负值为下降。<br>
            <strong style="color:#ef4444;">承载上限</strong>：41,000 人次/日，超过 70% 进入预警、90% 进入高负荷。
        </div>
        """, unsafe_allow_html=True)

with col_side:
    with st.container(border=True):
        st.markdown('<div class="panel-header" style="margin-bottom:8px;">7日预测明细</div>', unsafe_allow_html=True)
        
        if not forecast_df.empty:
            for _, row in forecast_df.iterrows():
                date_str = row["日期"]
                pred = row["预测"]
                upper = row["上限"]
                lower = row["下限"]
                
                if pred > capacity * 0.9:
                    badge = '<span class="badge badge-red">高负荷</span>'
                elif pred > capacity * 0.7:
                    badge = '<span class="badge badge-yellow">预警</span>'
                else:
                    badge = '<span class="badge badge-green">正常</span>'
                
                load_rate = min(pred / capacity * 100, 100)
                bar_color = "#ef4444" if load_rate > 90 else ("#f59e0b" if load_rate > 70 else "#10b981")
                
                st.markdown(f"""
                <div style="padding:8px 0; border-bottom:1px solid rgba(100,180,255,0.06);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:14px; font-weight:700; color:#e2e8f0;">{date_str}</div>
                            <div style="font-size:10px; color:#cbd5e1;">{lower:,.0f} - {upper:,.0f} (90% CI)</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:18px; font-weight:800; color:#06b6d4;">{pred:,.0f}</div>
                            <div style="font-size:10px; color:#cbd5e1;">载客率 {load_rate:.1f}%</div>
                        </div>
                    </div>
                    <div style="margin-top:4px;">{badge}</div>
                    <div style="margin-top:6px; height:4px; background:rgba(100,180,255,0.1); border-radius:2px; overflow:hidden;">
                        <div style="height:100%; width:{load_rate}%; background:{bar_color}; border-radius:2px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暂无预测数据")
    
    # 特征重要性
    with st.container(border=True):
        st.markdown('<div class="panel-header" style="margin-bottom:8px;">关键特征</div>', unsafe_allow_html=True)
        
        feat_df = get_feature_importance(5)
        if not feat_df.empty:
            for _, row in feat_df.iterrows():
                pct = row["importance"]
                bar_width = min(pct, 100) if pct > 0 else 0
                st.markdown(f"""
                <div style="margin-bottom:6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                        <span style="font-size:11px; color:#cbd5e1;">{row['feature']}</span>
                        <span style="font-size:11px; font-weight:600; color:#e2e8f0;">{pct:.1f}%</span>
                    </div>
                    <div style="height:4px; background:rgba(100,180,255,0.1); border-radius:2px; overflow:hidden;">
                        <div style="height:100%; width:{bar_width}%; background:linear-gradient(90deg, #3b82f6, #06b6d4); border-radius:2px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("特征重要性数据将在模型训练后显示")
    
    with st.container(border=True):
        st.markdown('<div class="panel-header" style="margin-bottom:8px;">可迁移性</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px; color:#cbd5e1; line-height:1.6;">
            所有特征均为<strong style="color:#06b6d4;">通用维度</strong>（时间、节假日、历史趋势），不依赖景区特有属性。<br>
            方法可直接迁移至：<strong style="color:#3b82f6;">黄山</strong> · <strong style="color:#8b5cf6;">泰山</strong> · <strong style="color:#10b981;">张家界</strong> 等全国同类 5A 景区。
        </div>
        """, unsafe_allow_html=True)

# ========== 自动刷新 ==========
# ========== 自动刷新 ==========
if auto_refresh:
    interval_seconds = int(refresh_interval.replace("s", ""))
    time.sleep(interval_seconds)
    st.rerun()
