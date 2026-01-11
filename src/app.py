"""
FastAPI 应用主入口
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import get_settings
from src.api import tasks, health
from src.core.scheduler import get_scheduler
from src.middleware import register_exception_handlers
from config.database import engine, Base

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
    logger.info(f"⭐⭐⭐⭐⭐⭐{settings.app_name} 启动完成⭐⭐⭐⭐⭐⭐")

    yield

    # 关闭时
    logger.info("任务调度器关闭中...")
    scheduler.shutdown()
    logger.info(f"⭐⭐⭐⭐⭐⭐{settings.app_name} 已停止⭐⭐⭐⭐⭐⭐\n\n\n")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        lifespan=lifespan
    )

    # 注册异常处理器
    register_exception_handlers(app)

    # 注册静态文件目录
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"静态文件目录已挂载: {static_dir}")

    # 注册路由
    app.include_router(health.router, tags=["Health"])
    app.include_router(tasks.router, prefix=settings.api_prefix, tags=["Tasks"])

    return app
