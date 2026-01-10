"""
FastAPI 应用主入口
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from src.api import tasks, health
from src.core.scheduler import get_scheduler
from config.database import engine,Base

logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时

    # 初始化数据库
    logger.info("初始化数据库...")
    Base.metadata.create_all(bind=engine)

    logger.info("任务调度器开始启动...")
    # 启动调度器
    scheduler = get_scheduler()
    scheduler.start()
    logger.info(f"⭐⭐⭐⭐⭐⭐{settings.APP_NAME} 启动完成⭐⭐⭐⭐⭐⭐")

    yield

    # 关闭时
    logger.info("任务调度器关闭中...")
    scheduler.shutdown()
    logger.info(f"⭐⭐⭐⭐⭐⭐{settings.APP_NAME} 已停止⭐⭐⭐⭐⭐⭐\n\n\n")

def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        lifespan=lifespan
    )

    # 注册路由
    app.include_router(health.router, tags=["Health"])
    app.include_router(tasks.router, prefix=settings.API_PREFIX, tags=["Tasks"])

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "detail": "Internal server error"}
        )

    return app
