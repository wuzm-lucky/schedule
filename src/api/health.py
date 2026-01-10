"""
健康检查接口
"""

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.scheduler import get_scheduler

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    scheduler_running: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    scheduler = get_scheduler()
    scheduler_running = scheduler.scheduler.running

    return HealthResponse(
        status="healthy" if scheduler_running else "unhealthy",
        scheduler_running=scheduler_running,
    )


@router.get("/ping")
async def ping():
    """简单的 ping 检查"""
    return {"pong": True}
