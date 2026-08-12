"""
项目全局配置 — 统一管理路径与文件名常量。
============================================
所有模块通过本文件获取目录/文件路径，避免硬编码散落各处；
改名、调整目录结构时只需在此同步，即可全局生效。

路径均基于项目根目录推导，跨运行目录、跨平台稳定。
"""
import os

# ===== 项目根目录 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===== 目录 =====
DATA_DIR = os.path.join(BASE_DIR, "data")
POWERBI_DATA_DIR = os.path.join(DATA_DIR, "powerbi")   # Power BI 星型模型数据（产出）
POWERBI_DIR = os.path.join(BASE_DIR, "powerbi")        # Power BI 脚本与规划文档
MODEL_DIR = os.path.join(BASE_DIR, "ml", "model")
UTILS_DIR = os.path.join(BASE_DIR, "utils")

# ===== data/ 文件 =====
RAW_XLSX = os.path.join(DATA_DIR, "jiuzhaigou_daily_2025.xlsx")   # 原始 Excel 存档（官网导出，需先转 CSV）
DAILY_CSV = os.path.join(DATA_DIR, "jiuzhaigou_daily.csv")        # 日度原始客流数据
FEATURES_CSV = os.path.join(DATA_DIR, "jiuzhaigou_features.csv")  # 特征化数据

# ===== powerbi/ 文件 =====
HOLIDAYS_CSV = os.path.join(POWERBI_DIR, "holidays_2019_2025.csv")  # 真实法定节假日

# ===== ml/model/ 文件 =====
XGBOOST_MODEL_PKL = os.path.join(MODEL_DIR, "xgboost_model.pkl")
SCALER_PKL = os.path.join(MODEL_DIR, "scaler.pkl")
FEATURE_NAMES_PKL = os.path.join(MODEL_DIR, "feature_names.pkl")
FEATURE_IMPORTANCE_CSV = os.path.join(MODEL_DIR, "feature_importance.csv")
MODEL_RESULTS_CSV = os.path.join(MODEL_DIR, "model_results.csv")

# ===== 节假日相关配置 =====
HOLIDAY_COVER_UNTIL_YEAR = 2027      # 节假日数据覆盖到该年份（未来年份自动用简化规则回退）
NEAR_HOLIDAY_DAYS = 3                # 临近节假日窗口：前后 N 天记为 near_holiday
GOLDEN_WEEK_RULES = {10: 7, 2: 5}    # 黄金周简化规则: {月份: 该月 1~N 日计为黄金周}
