# 🏔️ 峰流智测 · Scenic Flow Forecast

> 景区客流智能预测与运营决策平台 —— 让每一次客流高峰都「可预测、可预警、可决策」

以九寨沟景区真实官方数据为样板，构建从 **数据采集 → 特征工程 → 机器学习预测 → 可视化看板 → 运营决策 → BI 分析** 的全链路景区客流智能平台。XGBoost 时序预测模型在测试集上 **R²=0.9665、MAPE≈5.1%**，并提供未来 7 日滚动预测、承载量三色预警、自动运营建议与 RESTful API 服务。

---

## ✨ 核心功能

| 模块 | 说明 |
|------|------|
| 📊 运营总览看板 | 今日/均值/历史最高最低客流 KPI、客流趋势与 7 日预测叠加图、承载上限参考线 |
| 📈 客流分析 | 多维度真实数据分析：年度/月度/周内/节假日客流规律、峰谷识别、同比环比 |
| 🎉 节假日分析 | 真实节假日数据 × 客流交叉分析：哪个节最旺、节前节后效应、节假日类型对比 |
| 🔬 数据洞察 | 数据集概览、分布直方图 + KDE、Q-Q 正态检验、特征维度与数据质量评估 |
| 🤖 智能预测 | XGBoost 7 日滚动预测、90% 置信区间、R²/MAE/RMSE/MAPE 指标、特征重要性 |
| 🚨 运营决策 | 未来 7 日预警日历、风险分布、自动生成人员/物资/票务建议（红/黄/绿三色） |
| 🔌 RESTful API | Flask 提供健康检查、模型信息、客流预测、历史数据、特征重要性、决策建议接口 |
| 📊 Power BI 看板 | 星型模型 + DAX 度量值，4 页运营决策分析（总览/趋势/因素/预警） |

**三色预警机制**（承载上限 41,000 人次）：

- 🟢 **正常**：客流 ≤ 70% 承载量
- 🟡 **预警**：70% < 客流 ≤ 90% 承载量，建议提前疏导
- 🔴 **高负荷**：客流 > 90% 承载量，建议启动限流预案

---

## 🛠️ 技术栈

- **前端 / 可视化**：Streamlit、Plotly
- **机器学习**：XGBoost、scikit-learn（GridSearchCV + TimeSeriesSplit 时序交叉验证）、SHAP 可解释性
- **后端服务**：Flask + Flask-CORS（模型服务化）
- **数据处理**：Pandas、NumPy、Scipy
- **BI 分析**：Power BI（星型模型、DAX 度量值）、SQL
- **数据采集**：Python 增量爬虫（九寨沟官网）

---

## 📁 项目结构

```
scenic-flow-prediction/
├── streamlit.app.py          # Streamlit 主入口（运营总览首页）
├── config.py                 # 全局配置：统一路径与文件名常量
├── requirements.txt          # 运行时依赖清单
├── requirements-dev.txt      # 开发/测试依赖清单
├── .github/
│   └── workflows/ci.yml      # GitHub Actions CI（语法检查 + 单元测试）
│
├── api/                      # Flask RESTful API 服务
│   ├── main.py               # API 启动入口 (python -m api.main)
│   └── predict_api.py        # 路由与业务逻辑
│
├── data/                     # 数据层
│   ├── jiuzhaigou_scraper.py # 九寨沟官网增量爬虫
│   ├── clean_data.py         # 清洗 + 特征工程（40 维特征）
│   ├── jiuzhaigou_daily_2025.xlsx  # 原始 Excel 存档（官网导出，需先转 CSV）
│   ├── jiuzhaigou_daily.csv      # 日度原始客流数据
│   ├── jiuzhaigou_features.csv   # 特征化数据
│   └── powerbi/              # Power BI 星型模型数据
│
├── ml/                       # 机器学习层
│   ├── train_model.py        # 训练：多模型对比 + XGBoost 调优 + SHAP
│   └── model/                # 产出的模型与指标文件（已忽略入库）
│
├── pages/                    # Streamlit 多页面
│   ├── flow.py               # 客流分析
│   ├── holiday.py            # 节假日客流分析
│   ├── scenic.py             # 数据洞察
│   ├── predict.py            # 智能预测
│   ├── decision.py           # 运营决策
│   └── api_docs.py           # API 文档页
│
├── powerbi/                  # Power BI 规划、数据准备、DAX、SQL
│   ├── PowerBI看板规划_九寨沟客流.md
│   ├── PowerBI执行清单_九寨沟客流.md
│   ├── prepare_powerbi_data.py
│   └── rfm_analysis.sql
│
├── tests/                    # 单元测试（pytest）
│   ├── test_config.py
│   └── test_holidays.py
│
└── utils/                    # 共享工具
    ├── navbar.py             # 统一导航栏 / 深色主题 / 动态刷新
    ├── predictor.py          # 模型加载与预测封装
    └── holidays.py           # 统一节假日数据源（真实CSV + 未来年份回退）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 训练模型

```bash
python ml/train_model.py
```

流程：加载数据 → 特征工程 → 多模型对比（Linear / RandomForest / XGBoost）→ GridSearchCV 调优 → SHAP 解释 → 保存 `ml/model/` 下的模型与指标文件。

> 未训练模型时，应用会自动进入「演示模式」，使用模拟数据保证页面可预览。

### 3. 启动 Web 应用（Streamlit）

```bash
streamlit run streamlit.app.py
```

### 4. 启动 API 服务（Flask）

```bash
python -m api.main
```

服务默认运行于 `http://127.0.0.1:8000`，健康检查：`http://127.0.0.1:8000/api/health`

### 5. 运行单元测试

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## 📊 数据说明

- **数据源**：九寨沟景区官方网站每日进沟人数（`data/jiuzhaigou_scraper.py` 增量爬取）
- **样本规模**：2019-09 ~ 2025-03，共 **1,869 天**
- **特征维度**：**40 维**，覆盖时间特征、节假日特征、滞后特征、滚动统计特征
- **容量参考**：承载上限 **41,000 人次/日**
- **节假日数据**：`powerbi/holidays_2019_2025.csv` 真实法定节假日，经 [`utils/holidays.py`](utils/holidays.py:1) 统一加载（特征工程与预测共用，未来年份自动回退简化规则）

如需更新数据，可运行爬虫或执行 `data/clean_data.py` 重新构建特征。

> 原始 Excel（`data/jiuzhaigou_daily_2025.xlsx`）为官网导出存档，列结构非标准（非 `date,visitors`），使用前需先转为 CSV：
> ```bash
> python powerbi/xlsx_to_csv.py data/jiuzhaigou_daily_2025.xlsx data/jiuzhaigou_daily.csv
> ```

---

## 🧠 模型性能

多模型对比 + 超参调优后的最优模型（XGBoost，时序交叉验证）：

| 指标 | 数值 | 说明 |
|------|------|------|
| **R²** | 0.9665 | 决定系数，越接近 1 越好 |
| **MAE** | 997 人次 | 平均绝对误差 |
| **RMSE** | 1,769 人次 | 均方根误差（惩罚大偏差） |
| **MAPE** | 5.1% | 平均百分比误差 |

模型产出物（`ml/model/`）：

- `xgboost_model.pkl` — 训练好的 XGBoost 模型
- `scaler.pkl` / `feature_names.pkl` — 标准化器与特征名
- `feature_importance.csv` — 特征重要性排名
- `model_results.csv` — 多模型对比结果
- `prediction_examples.csv` — 预测示例

---

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + 模型加载状态 |
| GET | `/api/model/info` | 模型类型、数据源、特征维度、评估指标 |
| GET | `/api/forecast?days=7` | 未来 N 天客流预测（3-30），附承载率与预警标签 |
| GET | `/api/history?days=90` | 历史客流趋势 |
| GET | `/api/features/importance?top_n=15` | 特征重要性 Top N |
| GET | `/api/decision/suggestions` | 基于预测的运营决策建议 |

调用示例：

```bash
curl "http://127.0.0.1:8000/api/forecast?days=7"
```

---

## 📈 Power BI 决策看板

基于同一套九寨沟数据，按 **星型模型**（事实表 + 日期维 + 节假日维）建模，含总客流、日均客流、日饱和度、同比增幅、超载预警、预测区间覆盖率等 DAX 度量值，共 4 页：

1. **总览 KPI** — 年度客流、峰值日、承载力饱和度
2. **趋势与预测** — 实际 vs 预测 + 90% 置信带 + 同比
3. **因素分析** — 节假日客流、月度季节性、Top 驱动因子
4. **运营建议** — 未来 7 日预警表，条件格式高亮

规划与执行细节见 [`powerbi/PowerBI看板规划_九寨沟客流.md`](powerbi/PowerBI看板规划_九寨沟客流.md) 与 [`powerbi/PowerBI执行清单_九寨沟客流.md`](powerbi/PowerBI执行清单_九寨沟客流.md)。

---

## 🗺️ Roadmap

- [x] 数据采集与特征工程
- [x] XGBoost 客流预测模型（R²≈0.97）
- [x] Streamlit 多页运营看板
- [x] Flask RESTful API 服务化
- [x] Power BI 星型模型决策看板
- [x] 节假日数据源统一（真实节假日 CSV 替换硬编码）
- [x] 节假日客流分析页（节前节后效应 / 节日对比 / 类型分布）
- [ ] 接入更多景区数据（泛化到多景区）
- [ ] 实时客流监测与自动预警推送
- [ ] 历史预测误差回测与模型定期重训

---

## 📄 License

本项目仅用于学习与作品集演示，数据来源于九寨沟景区官方公开信息。
