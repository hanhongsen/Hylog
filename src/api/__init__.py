"""
API 模块（FastAPI）

提供 Hylog 系统的 HTTP 接口，把 ConversationAgent 的能力通过 RESTful API 暴露出来。

核心组件：
    app    - FastAPI 应用实例
    router - 会话与对话路由

使用方式：
    # 启动服务（在项目根目录）
    python main.py
    或
    uvicorn src.api.main:app --reload

    # 访问 Swagger 文档
    http://127.0.0.1:8000/docs

接口列表：
    POST   /api/sessions                       创建会话
    POST   /api/sessions/{session_id}/reply     提交回答
    GET    /api/sessions/{session_id}/state     查询进度
    GET    /api/sessions/{session_id}/result    查询结果
    GET    /api/sessions/{session_id}/messages  查询对话历史
"""

from .main import app
from .routes import router

__all__ = ["app", "router"]
