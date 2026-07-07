"""
Hylog API 服务启动入口

在项目根目录运行：
    python main.py

会读取 .env 中的配置（API_HOST / API_PORT / DB_PATH 等），
然后用 uvicorn 启动 FastAPI 应用。

启动后访问：
    http://127.0.0.1:8000/         健康检查
    http://127.0.0.1:8000/docs     Swagger API 文档
"""

import os

# 加载 .env 环境变量（开发阶段用）
from dotenv import load_dotenv
load_dotenv()

import uvicorn

from src.api.main import app  # noqa: E402


if __name__ == "__main__":
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,  # 开发阶段热重载，上线时可关闭
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
