"""
任务管理接口
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import get_settings
from src.core.scheduler import get_scheduler
from src.models import Task, TriggerType, CommonResponse


logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# ============ 请求/响应模型 ============


class ScriptInfo(BaseModel):
    """脚本信息"""
    name: str
    path: str
    size: int
    extension: str
    description: Optional[str] = None

class TaskAddRequest(BaseModel):
    """添加任务请求"""
    id: str
    name: str
    script_path: str
    trigger_type: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    scheduled_time: Optional[str] = None
    arguments: List[str] = []
    working_directory: Optional[str] = None
    environment: dict = {}
    timeout: int = 300
    enabled: bool = True
    description: Optional[str] = None


class TaskExecuteRequest(BaseModel):
    """立即执行任务请求"""
    task_id: str


class TaskResponse(BaseModel):
    """任务响应"""
    code: bool
    message: str
    data: Optional[dict] = None


# ============ 接口实现 ============

@router.get("/tasks", response_model=CommonResponse)
async def list_tasks():
    """获取所有任务列表"""
    scheduler = get_scheduler()
    jobs = scheduler.list_jobs()
    return CommonResponse(data=jobs)


@router.get("/scripts", response_model=CommonResponse)
async def list_scripts():
    """获取 scripts 目录中的所有脚本文件"""
    scripts_dir = Path(settings.SCRIPTS_DIR)

    if not scripts_dir.exists():
        return CommonResponse(scripts=[], code='not_found', message='脚本目录不存在')

    scripts = []
    # 支持的脚本扩展名
    supported_extensions = {'.py', '.sh', '.bat', '.cmd', '.js', '.ps1'}

    for file_path in scripts_dir.iterdir():
        # 跳过目录和隐藏文件
        if file_path.is_dir() or file_path.name.startswith('.'):
            continue

        ext = file_path.suffix.lower()
        if ext in supported_extensions:
            # 读取脚本第一行作为描述
            description = None
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('#!'):
                        # 跳过 shebang
                        second_line = f.readline().strip()
                        if second_line.startswith('#') or second_line.startswith('"""') or second_line.startswith("'''"):
                            description = second_line.lstrip('#"\'').strip()
                    elif first_line.startswith('#') or first_line.startswith('"""') or first_line.startswith("'''"):
                        description = first_line.lstrip('#"\'').strip()
            except Exception:
                pass

            scripts.append(ScriptInfo(
                name=file_path.name,
                path=str(file_path.relative_to(scripts_dir.parent)),
                size=file_path.stat().st_size,
                extension=ext,
                description=description
            ))

    return CommonResponse(data=scripts)


@router.get("/scripts/{script_name}")
async def get_script_content(script_name: str):
    """获取脚本内容"""
    scripts_dir = Path(settings.SCRIPTS_DIR)
    script_path = scripts_dir / script_name

    if not script_path.exists() or not script_path.is_file():
        raise HTTPException(status_code=404, detail="Script not found")

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()

        scriptContent = {
            "name": script_name,
            "path": str(script_path),
            "content": content
        }
        return CommonResponse(data=scriptContent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read script: {e}")


@router.post("/tasks", response_model=CommonResponse)
async def add_task(request: TaskAddRequest, background_tasks: BackgroundTasks):
    """添加新任务"""
    try:
        task = Task(
            id=request.id,
            name=request.name,
            script_path=request.script_path,
            trigger_type=TriggerType(request.trigger_type),
            cron_expression=request.cron_expression,
            interval_seconds=request.interval_seconds,
            arguments=request.arguments,
            working_directory=request.working_directory,
            environment=request.environment,
            timeout=request.timeout,
            enabled=request.enabled,
            description=request.description
        )

        scheduler = get_scheduler()
        success = scheduler.add_task(task)

        if success:
            return CommonResponse()
        else:
            raise HTTPException(status_code=500, detail="Failed to add task")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}", response_model=CommonResponse)
async def remove_task(task_id: str):
    """移除任务"""
    scheduler = get_scheduler()
    success = scheduler.remove_task(task_id)

    if success:
        return CommonResponse()
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/pause", response_model=CommonResponse)
async def pause_task(task_id: str):
    """暂停任务"""
    scheduler = get_scheduler()
    success = scheduler.pause_task(task_id)

    if success:
        return CommonResponse()
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/resume", response_model=CommonResponse)
async def resume_task(task_id: str):
    """恢复任务"""
    scheduler = get_scheduler()
    success = scheduler.resume_task(task_id)

    if success:
        return CommonResponse()
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.get("/tasks/{task_id}/next-run")
async def get_next_run_time(task_id: str):
    """获取任务下次执行时间"""
    scheduler = get_scheduler()
    next_run = scheduler.get_next_run_time(task_id)

    if next_run:
        return {"task_id": task_id, "next_run_time": next_run.isoformat()}
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/execute", response_model=CommonResponse)
async def execute_task_now(request: TaskExecuteRequest):
    """立即执行任务（不等待调度）"""
    # 这里需要从数据库获取任务配置
    # 暂时返回未实现
    return CommonResponse(
        code='unimplemented',
        message="Execute now feature requires database integration"
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_running_task(task_id: str):
    """取消正在运行的任务"""
    scheduler = get_scheduler()
    # 需要在 TaskExecutor 中实现取消逻辑
    return CommonResponse()

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # 找到项目根目录
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(BASE_DIR, "templates", "dashboard.html")
    try:
        with open(template_path, "r", encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>模板文件未找到: {template_path}</h1>")