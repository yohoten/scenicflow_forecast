"""config 模块路径常量测试"""
import os
import sys

# 确保项目根目录可被导入（config / utils 等共享模块）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config


def test_base_dir_is_project_root():
    """config.py 位于项目根，BASE_DIR 应等于 config.py 所在目录。"""
    assert config.BASE_DIR == os.path.dirname(os.path.abspath(config.__file__))


def test_directory_constants():
    """目录常量应指向预期子目录。"""
    assert config.DATA_DIR.endswith("data")
    assert config.POWERBI_DIR.endswith("powerbi")
    assert config.POWERBI_DATA_DIR.endswith(os.path.join("data", "powerbi"))
    assert config.MODEL_DIR.endswith(os.path.join("ml", "model"))
    assert config.UTILS_DIR.endswith("utils")


def test_key_file_paths():
    """关键数据/模型文件路径应组装正确（不要求文件存在，避免依赖数据仓库）。"""
    assert config.DAILY_CSV == os.path.join(config.DATA_DIR, "jiuzhaigou_daily.csv")
    assert config.FEATURES_CSV == os.path.join(config.DATA_DIR, "jiuzhaigou_features.csv")
    assert config.RAW_XLSX == os.path.join(config.DATA_DIR, "jiuzhaigou_daily_2025.xlsx")
    assert config.HOLIDAYS_CSV == os.path.join(config.POWERBI_DIR, "holidays_2019_2025.csv")
    assert config.XGBOOST_MODEL_PKL == os.path.join(config.MODEL_DIR, "xgboost_model.pkl")


def test_holiday_config():
    """节假日相关配置应合理。"""
    assert config.HOLIDAY_COVER_UNTIL_YEAR >= 2027
    assert config.NEAR_HOLIDAY_DAYS >= 1
    assert 10 in config.GOLDEN_WEEK_RULES   # 国庆
    assert 2 in config.GOLDEN_WEEK_RULES    # 春节
