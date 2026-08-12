"""
Flask API 启动入口
用法: python api/main.py
"""
from api.predict_api import app

if __name__ == "__main__":
    print("=" * 50)
    print("景区客流预测 API 服务启动")
    print("接口文档: http://127.0.0.1:8000/api/health")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8000, debug=False)
