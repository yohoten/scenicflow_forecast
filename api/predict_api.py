"""
景区客流预测 API (Flask)
提供模型预测、历史数据、特征重要性等 RESTful 接口
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from utils.predictor import (
    predict_next_7_days, get_model_metrics, get_feature_importance,
    generate_historical_trend, is_model_ready
)

app = Flask(__name__)
CORS(app)

CAPACITY = 41000


def _to_json(df):
    """DataFrame 转 JSON 友好格式"""
    if df is None or df.empty:
        return []
    result = df.copy()
    if "日期" in result.columns and pd.api.types.is_datetime64_any_dtype(result["日期"]):
        result["日期"] = result["日期"].dt.strftime("%Y-%m-%d")
    return result.to_dict(orient="records")


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "model_ready": is_model_ready(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/api/model/info", methods=["GET"])
def model_info():
    """模型基本信息和性能指标"""
    metrics = get_model_metrics()
    return jsonify({
        "model": "XGBoost Regression",
        "task": "景区每日客流量预测",
        "data_source": "九寨沟景区官方每日游客数据 (2019.9 - 2025.3)",
        "samples": 1869,
        "features": 40,
        "metrics": metrics,
        "capacity": CAPACITY,
        "model_ready": is_model_ready()
    })


@app.route("/api/forecast", methods=["GET"])
def forecast():
    """未来7日客流预测"""
    days = request.args.get("days", default=7, type=int)
    days = max(3, min(days, 30))

    df = predict_next_7_days(days=days)
    if df.empty:
        return jsonify({"success": False, "message": "模型未就绪，无法预测"}), 503

    result = _to_json(df)
    # 添加预警标签
    for item in result:
        pred = item.get("预测", 0)
        item["load_rate"] = round(pred / CAPACITY * 100, 1)
        if pred > CAPACITY * 0.9:
            item["warning"] = "danger"
            item["warning_text"] = "红色预警"
        elif pred > CAPACITY * 0.7:
            item["warning"] = "warning"
            item["warning_text"] = "黄色预警"
        else:
            item["warning"] = "normal"
            item["warning_text"] = "正常"

    return jsonify({
        "success": True,
        "capacity": CAPACITY,
        "forecast": result
    })


@app.route("/api/history", methods=["GET"])
def history():
    """历史客流趋势"""
    days = request.args.get("days", default=90, type=int)
    df = generate_historical_trend(days=days)
    return jsonify({
        "success": True,
        "count": len(df),
        "history": _to_json(df)
    })


@app.route("/api/features/importance", methods=["GET"])
def feature_importance():
    """特征重要性 Top N"""
    top_n = request.args.get("top_n", default=15, type=int)
    df = get_feature_importance(top_n=top_n)
    return jsonify({
        "success": True,
        "features": _to_json(df)
    })


@app.route("/api/decision/suggestions", methods=["GET"])
def decision_suggestions():
    """
    基于预测结果生成运营决策建议
    这是把模型结果转化为业务价值的关键接口
    """
    forecast_df = predict_next_7_days(days=7)
    if forecast_df.empty:
        return jsonify({"success": False, "message": "模型未就绪"}), 503

    hist_df = generate_historical_trend(days=30)
    suggestions = []

    # 1. 高峰预警
    max_idx = forecast_df["预测"].idxmax()
    peak_date_str = forecast_df.loc[max_idx, "完整日期"]
    peak_date = datetime.strptime(peak_date_str, "%Y-%m-%d")
    peak_value = forecast_df.loc[max_idx, "预测"]
    peak_load = peak_value / CAPACITY

    if peak_load > 0.9:
        suggestions.append({
            "level": "danger",
            "title": "启动红色限流预案",
            "date": peak_date_str,
            "content": f"{peak_date:%m月%d日} 预测客流 {peak_value:,.0f} 人次，达到承载量 {peak_load*100:.1f}%。建议提前 3 天启动分时段预约、关闭 OTA 当日票、增派 30% 安保人员。",
            "action": ["分时段预约", "限流措施", "增派安保"],
            "kpi": f"承载率 {peak_load*100:.1f}%"
        })
    elif peak_load > 0.75:
        suggestions.append({
            "level": "warning",
            "title": "高峰疏导准备",
            "date": peak_date_str,
            "content": f"{peak_date:%m月%d日} 预测客流 {peak_value:,.0f} 人次，承载率 {peak_load*100:.1f}%。建议开放备用通道、重点节点加派引导员。",
            "action": ["开放备用通道", "重点节点引导"],
            "kpi": f"承载率 {peak_load*100:.1f}%"
        })

    # 2. 低谷期运营建议
    min_idx = forecast_df["预测"].idxmin()
    valley_date_str = forecast_df.loc[min_idx, "完整日期"]
    valley_date = datetime.strptime(valley_date_str, "%Y-%m-%d")
    valley_value = forecast_df.loc[min_idx, "预测"]
    valley_load = valley_value / CAPACITY
    if valley_load < 0.3:
        suggestions.append({
            "level": "info",
            "title": "低谷期营销推广",
            "date": valley_date_str,
            "content": f"{valley_date:%m月%d日} 预测客流 {valley_value:,.0f} 人次，承载率仅 {valley_load*100:.1f}%。建议投放限时优惠票、推出本地居民半价活动、组织研学团。",
            "action": ["限时优惠", "本地营销", "研学团"],
            "kpi": f"承载率 {valley_load*100:.1f}%"
        })

    # 3. 趋势判断
    if not hist_df.empty:
        recent_7d = hist_df["客流量"].tail(7).mean()
        recent_30d = hist_df["客流量"].tail(30).mean()
        trend_change = (recent_7d - recent_30d) / recent_30d if recent_30d > 0 else 0

        if trend_change > 0.15:
            suggestions.append({
                "level": "warning",
                "title": "客流上升趋势明显",
                "date": "未来一周",
                "content": f"近7日均值 {recent_7d:,.0f} 人次，较30日均值 {recent_30d:,.0f} 人次上涨 {trend_change*100:.1f}%。建议提前增加摆渡车班次与售票窗口。",
                "action": ["增加摆渡车", "增设窗口"],
                "kpi": f"环比上涨 {trend_change*100:.1f}%"
            })
        elif trend_change < -0.15:
            suggestions.append({
                "level": "info",
                "title": "客流下降需关注",
                "date": "未来一周",
                "content": f"近7日均值 {recent_7d:,.0f} 人次，较30日均值 {recent_30d:,.0f} 人次下降 {abs(trend_change)*100:.1f}%。建议检查天气、竞品活动及舆情。",
                "action": ["舆情监控", "竞品分析"],
                "kpi": f"环比下降 {abs(trend_change)*100:.1f}%"
            })

    # 4. 人员配置建议
    avg_forecast = forecast_df["预测"].mean()
    if avg_forecast > CAPACITY * 0.6:
        staff_level = "高"
        staff_count = int(avg_forecast / 1000) + 80
    elif avg_forecast > CAPACITY * 0.3:
        staff_level = "中"
        staff_count = int(avg_forecast / 1000) + 50
    else:
        staff_level = "低"
        staff_count = int(avg_forecast / 1000) + 30

    suggestions.append({
        "level": "normal",
        "title": f"人员配置建议：{staff_level}等级",
        "date": "未来7日",
        "content": f"未来7日预测日均客流 {avg_forecast:,.0f} 人次，建议配置约 {staff_count} 名一线运营人员（含安检、引导、保洁、医疗）。",
        "action": ["排班系统", "人员调度"],
        "kpi": f"日均 {avg_forecast:,.0f} 人次"
    })

    return jsonify({
        "success": True,
        "capacity": CAPACITY,
        "suggestions": suggestions
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
