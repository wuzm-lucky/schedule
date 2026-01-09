import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

# 确保 app 包能被找到
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.api.routes import router
from app.scheduler.manager import scheduler
from app.database import engine, Base
from config import settings


# --- 1. 定义 lifespan 上下文管理器 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的逻辑
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    if not scheduler.running:
        scheduler.start()
        print("调度器已启动...")
    # yield 之后的部分是应用运行期间
    yield
    # 关闭时的逻辑
    if scheduler.running:
        scheduler.shutdown()
        print("调度器已关闭...")


# --- 2. 初始化 FastAPI 应用 ---
app = FastAPI(
    title="自动化任务调度系统",
    lifespan=lifespan  # <--- 绑定 lifespan
)
# 注册路由
app.include_router(router)
# --- 3. 入口运行逻辑 ---
if __name__ == "__main__":
    import uvicorn

    # 注意：在生产环境通常去掉 reload=True
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # 使用 .env 中的配置启动
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)