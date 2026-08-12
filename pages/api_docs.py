"""
景区客流预测平台 - API 文档页
展示 Flask RESTful API 接口说明与调用示例
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.navbar import render_navbar, render_sidebar

render_navbar("API文档")
auto_refresh, refresh_interval = render_sidebar()

st.markdown("""
<div style="margin-bottom:16px;">
    <span style="font-size:13px; color:#cbd5e1;">Flask RESTful API | 模型服务化 | 前后端分离</span>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="panel-header">服务启动</div>', unsafe_allow_html=True)
    st.code("python -m api.main", language="bash")
    st.markdown("""
    <div style="font-size:12px; color:#cbd5e1; line-height:1.8;">
        默认运行在 <code style="background:rgba(100,180,255,0.1); color:#3b82f6; padding:2px 6px; border-radius:4px;">http://127.0.0.1:5000</code>，
        支持 CORS 跨域。部署到生产环境时建议使用 Gunicorn + Nginx。
    </div>
    """, unsafe_allow_html=True)

BASE_URL = "http://127.0.0.1:5000"

api_endpoints = [
    {
        "name": "健康检查",
        "method": "GET",
        "path": "/api/health",
        "params": [],
        "desc": "检查 API 服务与模型加载状态",
        "example": f"curl {BASE_URL}/api/health",
        "response": """{
  "status": "ok",
  "model_ready": true,
  "timestamp": "2026-07-16 18:00:00"
}"""
    },
    {
        "name": "模型信息",
        "method": "GET",
        "path": "/api/model/info",
        "params": [],
        "desc": "获取模型类型、数据源、特征维度、评估指标",
        "example": f"curl {BASE_URL}/api/model/info",
        "response": """{
  "model": "XGBoost Regression",
  "task": "景区每日客流量预测",
  "data_source": "九寨沟景区官方每日游客数据 (2019.9 - 2025.3)",
  "samples": 1869,
  "features": 40,
  "metrics": {
    "r2": 0.9665,
    "mae": 997,
    "rmse": 1769,
    "mape": 5.1
  },
  "capacity": 41000,
  "model_ready": true
}"""
    },
    {
        "name": "客流预测",
        "method": "GET",
        "path": "/api/forecast",
        "params": [("days", "int", "3-30", "预测天数，默认 7")],
        "desc": "基于 XGBoost 模型滚动预测未来 N 天客流量，附带承载率预警标签",
        "example": f"curl \"{BASE_URL}/api/forecast?days=7\"",
        "response": """{
  "success": true,
  "capacity": 41000,
  "forecast": [
    {
      "日期": "03-25",
      "完整日期": "2026-03-25",
      "预测": 10421,
      "上限": 11984,
      "下限": 8858,
      "load_rate": 25.4,
      "warning": "normal",
      "warning_text": "正常"
    }
  ]
}"""
    },
    {
        "name": "历史数据",
        "method": "GET",
        "path": "/api/history",
        "params": [("days", "int", "1-999", "返回最近 N 天，默认 90")],
        "desc": "获取历史客流趋势数据，用于前端图表渲染",
        "example": f"curl \"{BASE_URL}/api/history?days=30\"",
        "response": """{
  "success": true,
  "count": 30,
  "history": [
    {
      "日期": "2026-02-24",
      "客流量": 8234
    }
  ]
}"""
    },
    {
        "name": "特征重要性",
        "method": "GET",
        "path": "/api/features/importance",
        "params": [("top_n", "int", "1-40", "返回 Top N 特征，默认 15")],
        "desc": "获取模型特征重要性排名（已归一化为百分比）",
        "example": f"curl \"{BASE_URL}/api/features/importance?top_n=10\"",
        "response": """{
  "success": true,
  "features": [
    {
      "feature": "visitors_roll_mean_3",
      "importance": 43.7
    }
  ]
}"""
    },
    {
        "name": "运营决策建议",
        "method": "GET",
        "path": "/api/decision/suggestions",
        "params": [],
        "desc": "基于未来7日预测与历史趋势生成业务级运营建议",
        "example": f"curl {BASE_URL}/api/decision/suggestions",
        "response": """{
  "success": true,
  "suggestions": [
    {
      "level": "warning",
      "title": "高峰疏导准备",
      "date": "2026-03-28",
      "content": "03月28日 预测客流 31,500 人次，承载率 76.8%。建议开放备用通道、重点节点加派引导员。",
      "action": ["开放备用通道", "重点节点引导"],
      "kpi": "承载率 76.8%"
    }
  ]
}"""
    },
]

for idx, api in enumerate(api_endpoints):
    with st.container(border=True):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                <span style="background:rgba(59,130,246,0.15); color:#3b82f6; padding:3px 10px; border-radius:6px; font-size:12px; font-weight:700;">{api['method']}</span>
                <span style="font-size:15px; font-weight:700; color:#f1f5f9;">{api['name']}</span>
            </div>
            <div style="font-size:13px; color:#06b6d4; font-family:monospace; margin-bottom:8px;">{api['path']}</div>
            <div style="font-size:12px; color:#cbd5e1; line-height:1.6; margin-bottom:10px;">{api['desc']}</div>
            """, unsafe_allow_html=True)
            
            if api['params']:
                st.markdown("<div style='font-size:12px; font-weight:600; color:#e2e8f0; margin-bottom:6px;'>请求参数</div>", unsafe_allow_html=True)
                for p_name, p_type, p_range, p_desc in api['params']:
                    st.markdown(f"""
                    <div style="display:flex; gap:8px; font-size:11px; color:#cbd5e1; margin-bottom:4px;">
                        <span style="color:#3b82f6; font-weight:600; min-width:60px;">{p_name}</span>
                        <span style="color:#94a3b8;">{p_type}</span>
                        <span style="color:#f59e0b;">{p_range}</span>
                        <span>{p_desc}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='font-size:12px; font-weight:600; color:#e2e8f0; margin:10px 0 6px;'>调用示例</div>", unsafe_allow_html=True)
            st.code(api['example'], language="bash")
        
        with col2:
            st.markdown("<div style='font-size:12px; font-weight:600; color:#e2e8f0; margin-bottom:6px;'>响应示例</div>", unsafe_allow_html=True)
            st.code(api['response'], language="json")

with st.container(border=True):
    st.markdown('<div class="panel-header">技术栈与部署</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px; color:#cbd5e1; line-height:1.8;">
        <strong style="color:#3b82f6;">后端框架</strong>：Flask 3.x + Flask-CORS<br>
        <strong style="color:#8b5cf6;">模型服务</strong>：XGBoost + joblib 延迟加载<br>
        <strong style="color:#10b981;">数据层</strong>：Pandas 读取本地 CSV，支持实时滚动预测<br>
        <strong style="color:#f59e0b;">部署方式</strong>：本地开发直接运行 api.main；生产环境建议使用 Gunicorn 或 Docker 容器化部署<br>
        <strong style="color:#06b6d4;">跨域支持</strong>：默认开启 CORS，前端 Streamlit / 第三方系统均可直接调用
    </div>
    """, unsafe_allow_html=True)

if auto_refresh:
    import time
    interval_seconds = int(refresh_interval.replace("s", ""))
    time.sleep(interval_seconds)
    st.rerun()
