"""
景区客流预测平台 - 运营决策建议页
将预测结果转化为可落地的业务建议
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.predictor import predict_next_7_days, get_model_metrics, generate_historical_trend, is_model_ready
from utils.navbar import render_navbar, render_sidebar

render_navbar("运营决策")
auto_refresh, refresh_interval = render_sidebar()

forecast_df = predict_next_7_days()
hist_df = generate_historical_trend(365)
metrics = get_model_metrics()
model_ready = is_model_ready()

capacity = 41000
high_load_threshold = capacity * 0.9
warning_threshold = capacity * 0.7

with st.container(border=True):
    st.markdown('<div class="panel-header">决策依据摘要</div>', unsafe_allow_html=True)
    if not forecast_df.empty:
        max_pred = forecast_df["预测"].max()
        max_date = forecast_df.loc[forecast_df["预测"].idxmax(), "完整日期"]
        avg_pred = forecast_df["预测"].mean()
        high_load_days = len(forecast_df[forecast_df["预测"] > high_load_threshold])
        warning_days = len(forecast_df[(forecast_df["预测"] > warning_threshold) & (forecast_df["预测"] <= high_load_threshold)])
        normal_days = len(forecast_df[forecast_df["预测"] <= warning_threshold])
        
        c1, c2, c3, c4, c5 = st.columns(5)
        summaries = [
            ("预测最高客流", f"{max_pred:,.0f}", max_date, "#ef4444"),
            ("7日平均预测", f"{avg_pred:,.0f}", "人次/天", "#3b82f6"),
            ("高负荷天数", f"{high_load_days}天", f"超 {high_load_threshold:,.0f} 人次", "#ef4444"),
            ("预警天数", f"{warning_days}天", f"超 {warning_threshold:,.0f} 人次", "#f59e0b"),
            ("正常天数", f"{normal_days}天", "安全区间", "#10b981"),
        ]
        for col, (label, value, sub, color) in zip([c1, c2, c3, c4, c5], summaries):
            with col:
                st.markdown(f"""
                <div style="background:linear-gradient(145deg, rgba(13,30,54,0.95) 0%, rgba(8,18,34,0.98) 100%); border:1px solid rgba(100,180,255,0.08); border-radius:12px; padding:16px; text-align:center; border-top:3px solid {color};">
                    <div style="font-size:11px; color:#cbd5e1; margin-bottom:4px;">{label}</div>
                    <div style="font-size:24px; font-weight:800; color:{color};">{value}</div>
                    <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">{sub}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("暂无预测数据，请完成模型训练")

if not forecast_df.empty:
    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container(border=True):
            st.markdown('<div class="panel-header">未来7日客流预警日历</div>', unsafe_allow_html=True)
            forecast_df["date"] = pd.to_datetime(forecast_df["完整日期"])
            forecast_df["星期"] = forecast_df["date"].dt.day_name().map({
                'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
                'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
            })
            forecast_df["load_rate"] = (forecast_df["预测"] / capacity * 100).clip(0, 100)
            forecast_df["status"] = forecast_df["预测"].apply(lambda x: "高负荷" if x > high_load_threshold else ("预警" if x > warning_threshold else "正常"))
            
            for _, row in forecast_df.iterrows():
                status_color = "#ef4444" if row["status"] == "高负荷" else ("#f59e0b" if row["status"] == "预警" else "#10b981")
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; margin-bottom:8px; background:rgba(13,30,54,0.6); border-radius:8px; border-left:4px solid {status_color};">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div>
                            <div style="font-size:14px; font-weight:700; color:#e2e8f0;">{row['完整日期']}</div>
                            <div style="font-size:11px; color:#cbd5e1;">{row['星期']}</div>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div style="text-align:right;">
                            <div style="font-size:18px; font-weight:800; color:#e2e8f0;">{row['预测']:,.0f}</div>
                            <div style="font-size:10px; color:#cbd5e1;">载客率 {row['load_rate']:.1f}%</div>
                        </div>
                        <div style="background:{status_color}20; color:{status_color}; padding:4px 12px; border-radius:12px; font-size:11px; font-weight:600; border:1px solid {status_color}40;">
                            {row['status']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        with st.container(border=True):
            st.markdown('<div class="panel-header">客流风险分布</div>', unsafe_allow_html=True)
            status_counts = forecast_df["status"].value_counts().to_dict()
            labels = ["正常", "预警", "高负荷"]
            values = [status_counts.get(s, 0) for s in labels]
            colors = ["#10b981", "#f59e0b", "#ef4444"]
            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values, hole=0.55,
                marker=dict(colors=colors, line=dict(color="#0a1628", width=2)),
                textinfo="label+percent", textfont=dict(color="#e2e8f0", size=12),
                hovertemplate="<b>%{label}</b><br>天数: %{value}<br>占比: %{percent}<extra></extra>"
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"),
                margin=dict(l=20, r=20, t=10, b=20), height=320, showlegend=False,
                annotations=[dict(text=f"{len(forecast_df)}天", x=0.5, y=0.5, font=dict(size=16, color="#e2e8f0"), showarrow=False)]
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        
        with st.container(border=True):
            st.markdown('<div class="panel-header">资源建议摘要</div>', unsafe_allow_html=True)
            if high_load_days > 0:
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.15); border-radius:8px; padding:12px; margin-bottom:10px;">
                    <div style="font-size:13px; font-weight:700; color:#f87171; margin-bottom:4px;">人员配置</div>
                    <div style="font-size:11px; color:#cbd5e1; line-height:1.5;">高负荷 {high_load_days} 天，建议比平时增派 <strong style="color:#e2e8f0;">30-50%</strong> 的安保与引导人员</div>
                </div>
                """, unsafe_allow_html=True)
            if warning_days > 0:
                st.markdown(f"""
                <div style="background:rgba(245,158,11,0.05); border:1px solid rgba(245,158,11,0.15); border-radius:8px; padding:12px; margin-bottom:10px;">
                    <div style="font-size:13px; font-weight:700; color:#fbbf24; margin-bottom:4px;">物资储备</div>
                    <div style="font-size:11px; color:#cbd5e1; line-height:1.5;">预警 {warning_days} 天，建议提前储备 <strong style="color:#e2e8f0;">20-30%</strong> 的餐饮和交通运力</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); border-radius:8px; padding:12px;">
                <div style="font-size:13px; font-weight:700; color:#34d399; margin-bottom:4px;">疏导策略</div>
                <div style="font-size:11px; color:#cbd5e1; line-height:1.5;">建议开放备用入口、延长开放时间、引导至次要景点错峰游览</div>
            </div>
            """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="panel-header">逐日运营建议</div>', unsafe_allow_html=True)
        for _, row in forecast_df.iterrows():
            pred = row["预测"]
            date = row["完整日期"]
            load_rate = pred / capacity * 100
            if pred > high_load_threshold:
                level = "danger"
                title = "红色预案：启动限流与分流"
                actions = [
                    "立即启动分时段预约机制，暂停当日现场售票",
                    "增派安保人员至核心景点（五花海、诺日朗瀑布等）",
                    "通过广播/APP 推送引导游客前往次要景点错峰",
                    "联系交警部门提前实施周边交通管制",
                ]
            elif pred > warning_threshold:
                level = "warning"
                title = "黄色预案：加强引导与储备"
                actions = [
                    "提前30%储备餐饮、饮水和医疗物资",
                    "增加景区接驳车班次，缩短候车时间",
                    "在拥堵节点设置临时引导员",
                    "准备限流预案，一旦客流继续攀升可立即执行",
                ]
            else:
                level = "normal"
                title = "绿色预案：维持正常运营"
                actions = [
                    "按常规人员配置运营",
                    "利用低峰时段进行设施维护和环境清洁",
                    "可适度推出优惠套票吸引周边游客",
                ]
            border_color = "#ef4444" if level == "danger" else ("#f59e0b" if level == "warning" else "#10b981")
            bg_color = "rgba(239,68,68,0.04)" if level == "danger" else ("rgba(245,158,11,0.04)" if level == "warning" else "rgba(16,185,129,0.04)")
            st.markdown(f"""
            <div style="background:{bg_color}; border:1px solid {border_color}30; border-radius:10px; padding:14px; margin-bottom:10px; border-left:4px solid {border_color};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div style="font-size:14px; font-weight:700; color:#e2e8f0;">{date} · {title}</div>
                    <div style="font-size:16px; font-weight:800; color:{border_color};">{pred:,.0f} 人次</div>
                </div>
                <div style="font-size:11px; color:#cbd5e1; margin-bottom:8px;">载客率 {load_rate:.1f}%</div>
                <ul style="margin:0; padding-left:16px; font-size:11px; color:#cbd5e1; line-height:1.8;">
                    {''.join([f'<li>{a}</li>' for a in actions])}
                </ul>
            </div>
            """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="panel-header">业务价值量化</div>', unsafe_allow_html=True)
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            if not hist_df.empty:
                hist_avg = hist_df["客流量"].tail(30).mean()
                pred_avg = forecast_df["预测"].mean()
                diff = pred_avg - hist_avg
                st.markdown(f"""
                <div style="background:rgba(59,130,246,0.05); border:1px solid rgba(59,130,246,0.15); border-radius:12px; padding:16px; text-align:center;">
                    <div style="font-size:11px; color:#cbd5e1; margin-bottom:4px;">7日预测均值 vs 近30天均值</div>
                    <div style="font-size:22px; font-weight:800; color:#3b82f6;">{diff:+,.0f}</div>
                    <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">人次 / 天</div>
                </div>
                """, unsafe_allow_html=True)
        with col_v2:
            if metrics and metrics.get('r2', 0) > 0:
                r2 = metrics.get('r2')
                st.markdown(f"""
                <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.15); border-radius:12px; padding:16px; text-align:center;">
                    <div style="font-size:11px; color:#cbd5e1; margin-bottom:4px;">预测准确度</div>
                    <div style="font-size:22px; font-weight:800; color:#10b981;">{r2:.4f}</div>
                    <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">R² 决定系数</div>
                </div>
                """, unsafe_allow_html=True)
        with col_v3:
            if not hist_df.empty and not forecast_df.empty:
                mape = metrics.get('mape', 5.0)
                potential_savings = forecast_df["预测"].sum() * (mape / 100) * 2  # 假设每次误调配成本2元
                st.markdown(f"""
                <div style="background:rgba(245,158,11,0.05); border:1px solid rgba(245,158,11,0.15); border-radius:12px; padding:16px; text-align:center;">
                    <div style="font-size:11px; color:#cbd5e1; margin-bottom:4px;">潜在资源优化价值</div>
                    <div style="font-size:22px; font-weight:800; color:#f59e0b;">¥{potential_savings:,.0f}</div>
                    <div style="font-size:10px; color:#cbd5e1; margin-top:4px;">7日预测周期</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="margin-top:16px; padding:12px; background:rgba(15,38,66,0.5); border-radius:8px; font-size:11px; color:#cbd5e1; line-height:1.6;">
            <strong style="color:#e2e8f0;">说明：</strong> 潜在资源优化价值基于预测误差降低后减少的过度配置与应急支出估算。
            模型准确度越高，景区越能精准匹配人力、物资与交通资源，避免旺季资源不足和淡季资源浪费。
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:20px; padding:16px; background:rgba(15,38,66,0.5); border-radius:12px; border:1px solid rgba(100,180,255,0.08); text-align:center;">
    <div style="font-size:12px; color:#cbd5e1;">
        运营决策建议基于 XGBoost 7日预测结果自动生成 · 建议结合实际天气、节假日政策灵活调整
    </div>
</div>
""", unsafe_allow_html=True)

if auto_refresh:
    interval_seconds = int(refresh_interval.replace("s", ""))
    time.sleep(interval_seconds)
    st.rerun()
