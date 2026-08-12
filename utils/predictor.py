"""
景区客流预测器 — 加载训练好的XGBoost模型进行预测
供 Streamlit predict.py 页面调用
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# 确保项目根目录可被导入（config 等共享模块）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import MODEL_DIR, DATA_DIR

# ===== 模型加载 =====
_model = None
_scaler = None
_features = None
_model_loaded = False
_model_metrics = None

def _load_model():
    """延迟加载模型"""
    global _model, _scaler, _features, _model_loaded, _model_metrics
    
    if _model_loaded:
        return
    
    model_path = os.path.join(MODEL_DIR, "xgboost_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    feat_path = os.path.join(MODEL_DIR, "feature_names.pkl")
    
    if not os.path.exists(model_path):
        print(f"[警告] 模型文件不存在: {model_path}")
        print("  请先运行 ml/train_model.py 训练模型")
        return
    
    try:
        _model = joblib.load(model_path)
        _scaler = joblib.load(scaler_path)
        _features = joblib.load(feat_path)
        _model_loaded = True
    except Exception as e:
        print(f"[错误] 模型加载失败: {e}")
        return
    
    # 加载模型指标
    results_path = os.path.join(MODEL_DIR, "model_results.csv")
    if os.path.exists(results_path):
        results = pd.read_csv(results_path, index_col=0)
        if "XGBoost (最优)" in results.index:
            row = results.loc["XGBoost (最优)"]
            _model_metrics = {
                "r2": round(row["R²"], 4),
                "mae": round(row["MAE"], 0),
                "rmse": round(row["RMSE"], 0),
                "mape": round(row["MAPE"], 1),
            }


def is_model_ready():
    """检查模型是否就绪"""
    return os.path.exists(os.path.join(MODEL_DIR, "xgboost_model.pkl"))


def get_model_metrics():
    """获取模型评估指标"""
    _load_model()
    return _model_metrics or {}


def get_feature_importance(top_n=15):
    """获取特征重要性排名（归一化为百分比）"""
    imp_path = os.path.join(MODEL_DIR, "feature_importance.csv")
    if os.path.exists(imp_path):
        df = pd.read_csv(imp_path)
        # 按重要性排序并取 top_n
        df = df.sort_values("importance", ascending=False).head(top_n).reset_index(drop=True)
        # 归一化为百分比（基于 top_n 的总和）
        total = df["importance"].sum()
        if total > 0:
            df["importance"] = df["importance"] / total * 100
        return df
    return pd.DataFrame()


def predict_next_7_days(days=7):
    """预测未来 N 天客流量（默认7天）"""
    _load_model()
    
    if _model is None:
        return _mock_prediction_7days(days=days)
    
    # 加载历史数据
    features_path = os.path.join(DATA_DIR, "jiuzhaigou_features.csv")
    if not os.path.exists(features_path):
        raw_path = os.path.join(DATA_DIR, "jiuzhaigou_daily.csv")
        if not os.path.exists(raw_path):
            return _mock_prediction_7days(days=days)
        
        df = pd.read_csv(raw_path, encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        latest_date = df["date"].max()
        latest_visitors = df["visitors"].values
        dates_list = df["date"].tolist()
    else:
        df_full = pd.read_csv(features_path, encoding="utf-8-sig")
        df_full["date"] = pd.to_datetime(df_full["date"])
        df_full = df_full.sort_values("date").reset_index(drop=True)
        latest_date = df_full["date"].max()
        latest_visitors = df_full["visitors"].values
        dates_list = df_full["date"].tolist()
    
    # 爬取节假日
    holidays = _get_holidays()
    
    predictions = []
    pred_dates = []
    
    # 滚动历史值
    recent_visitors = list(latest_visitors[-60:])  # 最近60天
    
    for day_offset in range(1, days + 1):
        pred_date = latest_date + timedelta(days=day_offset)
        pred_dates.append(pred_date)
        
        # 构建特征向量
        features_dict = {}
        
        # 时间特征
        features_dict["year"] = pred_date.year
        features_dict["month"] = pred_date.month
        features_dict["day"] = pred_date.day
        features_dict["day_of_week"] = pred_date.dayofweek
        features_dict["is_weekend"] = 1 if pred_date.dayofweek >= 5 else 0
        features_dict["day_of_year"] = pred_date.timetuple().tm_yday
        features_dict["week_of_year"] = pred_date.isocalendar()[1]
        features_dict["quarter"] = (pred_date.month - 1) // 3 + 1
        features_dict["is_month_start"] = 1 if pred_date.day == 1 else 0
        features_dict["is_month_end"] = 1 if pred_date.day == pred_date.days_in_month else 0
        
        # 节假日特征
        date_str = pred_date.strftime("%Y-%m-%d")
        features_dict["is_holiday"] = 1 if date_str in holidays else 0
        features_dict["near_holiday"] = _check_near_holiday(pred_date, holidays)
        features_dict["is_summer"] = 1 if pred_date.month in [7, 8] else 0
        features_dict["is_golden_week"] = 1 if ((pred_date.month == 10 and pred_date.day <= 7) or 
                                                  (pred_date.month == 2 and pred_date.day <= 5)) else 0
        features_dict["is_peak_season"] = 1 if pred_date.month in [4, 5, 6, 7, 8, 9, 10, 11] else 0
        
        # 滞后特征
        for lag in [1, 2, 3, 7]:
            idx = -lag
            features_dict[f"visitors_lag_{lag}"] = recent_visitors[idx] if abs(idx) <= len(recent_visitors) else recent_visitors[-1]
        
        # 滚动统计（基于历史）
        visitors_array = np.array(recent_visitors[-30:])
        for window in [3, 7, 14, 30]:
            w = min(window, len(visitors_array))
            arr = visitors_array[-w:]
            features_dict[f"visitors_roll_mean_{window}"] = arr.mean()
            features_dict[f"visitors_roll_std_{window}"] = arr.std() if len(arr) > 1 else 0
            features_dict[f"visitors_roll_max_{window}"] = arr.max()
            features_dict[f"visitors_roll_min_{window}"] = arr.min()
        
        # 365天前
        year_ago = pred_date - timedelta(days=365)
        year_ago_date = year_ago.strftime("%Y-%m-%d")
        # 在历史数据中找
        found_365 = None
        for i, d in enumerate(dates_list):
            if d.strftime("%Y-%m-%d") == year_ago_date:
                found_365 = latest_visitors[i]
                break
        features_dict["visitors_lag_365"] = found_365 if found_365 is not None else visitors_array.mean()
        
        # 差分
        features_dict["visitors_diff_1"] = recent_visitors[-1] - (recent_visitors[-2] if len(recent_visitors) >= 2 else recent_visitors[-1])
        features_dict["visitors_diff_7"] = recent_visitors[-1] - (recent_visitors[-7] if len(recent_visitors) >= 7 else recent_visitors[-1])
        
        # 周环比
        wow = (recent_visitors[-1] - recent_visitors[-7]) / recent_visitors[-7] if len(recent_visitors) >= 7 and recent_visitors[-7] != 0 else 0
        features_dict["visitors_wow"] = wow
        
        # 趋势强度
        mean7 = np.mean(visitors_array[-7:]) if len(visitors_array) >= 7 else visitors_array.mean()
        mean30 = visitors_array.mean()
        features_dict["trend_strength"] = mean7 / mean30 if mean30 > 0 else 1.0
        
        # 构建特征向量（按训练时的顺序）
        feature_vec = np.array([features_dict.get(f, 0) for f in _features]).reshape(1, -1)
        
        # 预测
        feature_scaled = _scaler.transform(feature_vec)
        pred = _model.predict(feature_scaled)[0]
        pred = max(0, pred)
        
        predictions.append(round(pred, 0))
        recent_visitors.append(pred)  # 滚动更新
    
    return pd.DataFrame({
        "日期": [d.strftime("%m-%d") for d in pred_dates],
        "预测": [int(p) for p in predictions],
        "上限": [int(p * 1.15) for p in predictions],
        "下限": [int(p * 0.85) for p in predictions],
        "完整日期": [d.strftime("%Y-%m-%d") for d in pred_dates],
    })


def _get_holidays():
    """获取节假日集合（真实节假日 CSV 优先 + 未来年份简化回退）"""
    from utils.holidays import get_holiday_set
    return get_holiday_set(cover_until_year=2027)


def _check_near_holiday(date, holidays):
    for delta in range(-3, 4):
        check_date = (date + timedelta(days=delta)).strftime("%Y-%m-%d")
        if check_date in holidays and delta != 0:
            return 1
    return 0


def _mock_prediction_7days(days=7):
    """模型未就绪时的模拟预测（有明确提示）"""
    dates = [(datetime.now() + timedelta(days=i)).strftime("%m-%d") for i in range(1, days + 1)]
    base = 15000
    np.random.seed(42)
    preds = base + np.random.normal(0, 2000, days).astype(int)
    return pd.DataFrame({
        "日期": dates,
        "预测": [max(0, int(p)) for p in preds],
        "上限": [max(0, int(p * 1.15)) for p in preds],
        "下限": [max(0, int(p * 0.85)) for p in preds],
        "完整日期": [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, days + 1)],
    })


def generate_historical_trend(days=30):
    """生成历史客流趋势（用于图表展示）"""
    features_path = os.path.join(DATA_DIR, "jiuzhaigou_features.csv")
    raw_path = os.path.join(DATA_DIR, "jiuzhaigou_daily.csv")
    
    if os.path.exists(features_path):
        df = pd.read_csv(features_path, encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"])
    elif os.path.exists(raw_path):
        df = pd.read_csv(raw_path, encoding="utf-8-sig")
        df["date"] = pd.to_datetime(df["date"])
    else:
        dates = pd.date_range(end=datetime.now(), periods=days)
        np.random.seed(42)
        base = 15000 + 5000 * np.sin(np.arange(days) * 2 * np.pi / 365)
        visitors = base + np.random.normal(0, 2000, days)
        return pd.DataFrame({"日期": dates, "客流量": visitors.astype(int)})
    
    recent = df.sort_values("date").tail(days)
    return pd.DataFrame({
        "日期": recent["date"],
        "客流量": recent["visitors"].astype(int),
    })
