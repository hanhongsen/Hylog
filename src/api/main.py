"""
FastAPI 应用入口

定义 Hylog 的 FastAPI 应用实例，负责：
- 创建应用、配置元信息
- CORS 中间件（允许前端跨域访问）
- 启动时初始化数据库（全局单例）
- 全局异常处理（统一错误响应格式）
- 注册路由

启动方式（在项目根目录）：
    python main.py
    或
    uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
"""

import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.data import init_global_database, get_database_url

from .routes import router as api_router


# ============================================================
# 日志配置
# ============================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(
    title="Hylog API",
    description=(
        "Hylog（嗨，老己）AI 人格建模与人物匹配系统后端。\n\n"
        "通过自然对话动态建模用户人格（OCEAN 五维），"
        "并将用户匹配到中国历史上的著名人物（清朝或之前）。"
    ),
    version="0.1.0",
)


# ============================================================
# CORS 中间件
# ============================================================

# 允许跨域的前端来源（逗号分隔），默认允许 Streamlit 默认端口
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 启动事件：初始化数据库
# ============================================================

@app.on_event("startup")
def on_startup():
    """
    应用启动时初始化数据库（全局单例）

    - 读取 DB_PATH 配置（默认 hylog.db）
    - 调用 init_global_database 建表 + 创建 engine 单例
    """
    db_path = os.getenv("DB_PATH", "hylog.db")
    db_url = get_database_url("sqlite", db_path)
    try:
        init_global_database(db_url)
        logger.info(f"数据库已初始化: {db_url}")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        raise


# ============================================================
# 全局异常处理
# ============================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    兜底异常处理：所有未捕获的异常统一返回 500，避免堆栈泄露给前端
    """
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {exc}", "error_code": "INTERNAL_ERROR"},
    )


# ============================================================
# 注册路由
# ============================================================

app.include_router(api_router)


# ============================================================
# 健康检查
# ============================================================

@app.get("/", tags=["系统"], summary="健康检查")
def health_check():
    """根路径健康检查，确认服务是否正常运行"""
    return {"status": "ok", "service": "Hylog API", "version": "0.1.0"}
