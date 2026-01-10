"""
任务管理接口
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Query
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
    task_name: str
    func_name: str
    trigger_type: str
    trigger_args: dict = {}
    args: List[str] = []

    # 完整格式（可选）
    id: Optional[str] = None
    script_path: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    scheduled_time: Optional[str] = None
    arguments: List[str] = []
    working_directory: Optional[str] = None
    environment: dict = {}
    timeout: int = 300
    enabled: bool = True
    description: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    script_path: Optional[str] = None
    trigger_type: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    arguments: List[str] = []
    working_directory: Optional[str] = None
    timeout: Optional[int] = None


class TaskExecuteRequest(BaseModel):
    """立即执行任务请求"""
    task_id: str


class TaskQueryRequest(BaseModel):
    """任务查询请求"""
    keyword: Optional[str] = None
    enabled: Optional[bool] = None
    trigger_type: Optional[str] = None


# ============ 接口实现 ============


@router.get("/tasks", response_model=CommonResponse)
async def list_tasks(
    keyword: Optional[str] = None,
    enabled: Optional[bool] = None,
    include_deleted: bool = False
):
    """获取所有任务列表"""
    from config.database import SessionLocal
    from src.models.database import TaskModel

    db = SessionLocal()
    try:
        query = db.query(TaskModel)

        # 过滤已删除的任务
        if not include_deleted:
            query = query.filter(TaskModel.deleted == False)

        # 关键词搜索
        if keyword:
            query = query.filter(TaskModel.name.like(f"%{keyword}%"))

        # 状态过滤
        if enabled is not None:
            query = query.filter(TaskModel.enabled == enabled)

        tasks = query.order_by(TaskModel.created_at.desc()).all()
        scheduler = get_scheduler()

        result = []
        for tm in tasks:
            next_run_time = scheduler.get_next_run_time(tm.id)
            result.append({
                "id": tm.id,
                "name": tm.name,
                "script_path": tm.script_path,
                "trigger_type": tm.trigger_type,
                "enabled": tm.enabled,
                "deleted": tm.deleted,
                "run_count": tm.run_count,
                "success_count": tm.success_count,
                "failed_count": tm.failed_count,
                "next_run_time": next_run_time.isoformat() if next_run_time else None,
                "description": tm.description,
                "cron_expression": tm.cron_expression,
                "interval_seconds": tm.interval_seconds,
                "created_at": tm.created_at.isoformat() if tm.created_at else None,
                "updated_at": tm.updated_at.isoformat() if tm.updated_at else None
            })

        return CommonResponse(data=result)
    finally:
        db.close()


@router.post("/tasks/query", response_model=CommonResponse)
async def query_tasks(query: TaskQueryRequest):
    """查询任务"""
    from config.database import SessionLocal
    from src.models.database import TaskModel

    db = SessionLocal()
    try:
        q = db.query(TaskModel).filter(TaskModel.deleted == False)

        if query.keyword:
            q = q.filter(TaskModel.name.like(f"%{query.keyword}%"))
        if query.enabled is not None:
            q = q.filter(TaskModel.enabled == query.enabled)
        if query.trigger_type:
            q = q.filter(TaskModel.trigger_type == query.trigger_type)

        tasks = q.order_by(TaskModel.created_at.desc()).all()
        scheduler = get_scheduler()

        result = []
        for tm in tasks:
            next_run_time = scheduler.get_next_run_time(tm.id)
            result.append({
                "id": tm.id,
                "name": tm.name,
                "script_path": tm.script_path,
                "trigger_type": tm.trigger_type,
                "enabled": tm.enabled,
                "run_count": tm.run_count,
                "success_count": tm.success_count,
                "failed_count": tm.failed_count,
                "next_run_time": next_run_time.isoformat() if next_run_time else None,
                "description": tm.description,
                "cron_expression": tm.cron_expression,
                "interval_seconds": tm.interval_seconds
            })

        return CommonResponse(data=result)
    finally:
        db.close()


@router.get("/tasks/{task_id}", response_model=CommonResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    scheduler = get_scheduler()
    task = scheduler.get_task_from_db(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from config.database import SessionLocal
    from src.models.database import TaskModel

    db = SessionLocal()
    try:
        tm = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        next_run_time = scheduler.get_next_run_time(task_id)

        return CommonResponse(data={
            "id": tm.id,
            "name": tm.name,
            "script_path": tm.script_path,
            "trigger_type": tm.trigger_type,
            "enabled": tm.enabled,
            "deleted": tm.deleted,
            "run_count": tm.run_count,
            "success_count": tm.success_count,
            "failed_count": tm.failed_count,
            "next_run_time": next_run_time.isoformat() if next_run_time else None,
            "description": tm.description,
            "cron_expression": tm.cron_expression,
            "interval_seconds": tm.interval_seconds,
            "arguments": tm.arguments,
            "working_directory": tm.working_directory,
            "timeout": tm.timeout,
            "created_at": tm.created_at.isoformat() if tm.created_at else None,
            "updated_at": tm.updated_at.isoformat() if tm.updated_at else None
        })
    finally:
        db.close()


@router.get("/scripts", response_model=CommonResponse)
async def list_scripts():
    """获取 scripts 目录中的所有脚本文件"""
    scripts_dir = Path(settings.SCRIPTS_DIR)

    if not scripts_dir.exists():
        return CommonResponse(scripts=[], code='not_found', message='脚本目录不存在')

    scripts = []
    supported_extensions = {'.py', '.sh', '.bat', '.cmd', '.js', '.ps1'}

    for file_path in scripts_dir.iterdir():
        if file_path.is_dir() or file_path.name.startswith('.'):
            continue

        ext = file_path.suffix.lower()
        if ext in supported_extensions:
            description = None
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('#!'):
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


@router.post("/tasks", response_model=CommonResponse)
async def add_task(request: TaskAddRequest, background_tasks: BackgroundTasks):
    """添加新任务"""
    try:
        scheduler = get_scheduler()

        task_id = request.id or str(uuid.uuid4())
        script_path = request.script_path or request.func_name

        trigger_type = TriggerType(request.trigger_type)
        cron_expression = request.cron_expression
        interval_seconds = request.interval_seconds
        scheduled_time = None

        if trigger_type == TriggerType.CRON:
            if request.trigger_args and not cron_expression:
                hour = request.trigger_args.get("hour", "*")
                minute = request.trigger_args.get("minute", "*")
                second = request.trigger_args.get("second", "0")
                cron_expression = f"{second} {minute} {hour} * * *"
        elif trigger_type == TriggerType.INTERVAL:
            interval_seconds = request.interval_seconds or request.trigger_args.get("seconds", 60)
        elif trigger_type == TriggerType.DATE:
            if request.trigger_args and request.trigger_args.get("run_date"):
                scheduled_time = datetime.fromisoformat(request.trigger_args["run_date"])

        task = Task(
            id=task_id,
            name=request.task_name,
            script_path=script_path,
            trigger_type=trigger_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            scheduled_time=scheduled_time,
            arguments=request.arguments or request.args,
            working_directory=request.working_directory,
            environment=request.environment,
            timeout=request.timeout,
            enabled=request.enabled,
            description=request.description
        )

        # 只保存到数据库，不添加到调度器
        success = scheduler.add_task(task)

        if success:
            return CommonResponse(message="任务添加成功")
        else:
            raise HTTPException(status_code=500, detail="Failed to add task")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tasks/{task_id}", response_model=CommonResponse)
async def update_task(task_id: str, request: TaskUpdateRequest):
    """更新任务"""
    from config.database import SessionLocal
    from src.models.database import TaskModel

    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # 更新可修改的字段
        if request.name is not None:
            task.name = request.name
        if request.enabled is not None:
            task.enabled = request.enabled
        if request.description is not None:
            task.description = request.description
        if request.script_path is not None:
            task.script_path = request.script_path
        if request.trigger_type is not None:
            task.trigger_type = request.trigger_type
        if request.cron_expression is not None:
            task.cron_expression = request.cron_expression
        if request.interval_seconds is not None:
            task.interval_seconds = request.interval_seconds
        if request.arguments is not None:
            task.arguments = json.dumps(request.arguments) if request.arguments else None
        if request.working_directory is not None:
            task.working_directory = request.working_directory
        if request.timeout is not None:
            task.timeout = request.timeout

        db.commit()

        # 如果启用状态改变，同步更新调度器
        if request.enabled is not None:
            scheduler = get_scheduler()
            if request.enabled:
                scheduler.resume_task(task_id)
            else:
                scheduler.pause_task(task_id)

        return CommonResponse(message="任务更新成功")
    finally:
        db.close()


@router.delete("/tasks/{task_id}", response_model=CommonResponse)
async def remove_task(task_id: str):
    """删除任务（逻辑删除）"""
    from config.database import SessionLocal
    from src.models.database import TaskModel

    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # 逻辑删除
        task.deleted = True
        task.enabled = False
        db.commit()

        # 从调度器移除
        scheduler = get_scheduler()
        scheduler.remove_task(task_id, remove_from_db=False)

        return CommonResponse(message="任务删除成功")
    finally:
        db.close()


@router.post("/tasks/{task_id}/restore", response_model=CommonResponse)
async def restore_task(task_id: str):
    """恢复已删除的任务"""
    from config.database import SessionLocal
    from src.models.database import TaskModel

    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task.deleted = False
        task.enabled = True
        db.commit()

        # 重新添加到调度器
        scheduler = get_scheduler()
        from src.models.task import TriggerType
        tm_task = Task(
            id=task.id,
            name=task.name,
            script_path=task.script_path,
            trigger_type=TriggerType(task.trigger_type),
            cron_expression=task.cron_expression,
            interval_seconds=task.interval_seconds,
            scheduled_time=task.scheduled_time,
            arguments=[],
            timeout=task.timeout,
            enabled=task.enabled,
            description=task.description
        )
        scheduler.add_task(tm_task)

        return CommonResponse(message="任务恢复成功")
    finally:
        db.close()


@router.post("/tasks/{task_id}/pause", response_model=CommonResponse)
async def pause_task(task_id: str):
    """暂停任务"""
    scheduler = get_scheduler()
    success = scheduler.pause_task(task_id)

    if success:
        return CommonResponse(message="任务暂停成功")
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/resume", response_model=CommonResponse)
async def resume_task(task_id: str):
    """恢复任务"""
    scheduler = get_scheduler()
    success = scheduler.resume_task(task_id)

    if success:
        return CommonResponse(message="任务恢复成功")
    else:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/execute", response_model=CommonResponse)
async def execute_task_now(request: TaskExecuteRequest):
    """立即执行任务"""
    scheduler = get_scheduler()
    task = scheduler.get_task_from_db(request.task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    import threading
    from src.core.scheduler import _execute_task_wrapper
    def run_task():
        try:
            _execute_task_wrapper(task.id)
        except Exception as e:
            logger.error(f"Error executing task: {e}")

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()

    return CommonResponse(message="任务已触发执行")


@router.post("/tasks/run/{task_id}", response_model=CommonResponse)
async def run_task(task_id: str):
    """立即执行任务（前端路径兼容）"""
    request = TaskExecuteRequest(task_id=task_id)
    return await execute_task_now(request)


@router.get("/tasks/{task_id}/executions", response_model=CommonResponse)
async def get_task_executions(
    task_id: str,
    limit: int = Query(50, le=200),
    status: Optional[str] = None
):
    """获取任务执行记录"""
    from config.database import SessionLocal
    from src.models.database import TaskExecutionModel

    db = SessionLocal()
    try:
        query = db.query(TaskExecutionModel).filter(TaskExecutionModel.task_id == task_id)

        if status:
            query = query.filter(TaskExecutionModel.status == status)

        executions = query.order_by(TaskExecutionModel.start_time.desc()).limit(limit).all()

        result = []
        for e in executions:
            result.append({
                "id": e.id,
                "task_id": e.task_id,
                "task_name": e.task_name,
                "status": e.status,
                "start_time": e.start_time.isoformat() if e.start_time else None,
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "duration": e.duration,
                "exit_code": e.exit_code,
                "output": e.output,
                "error": e.error
            })

        return CommonResponse(data=result)
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(BASE_DIR, "templates", "dashboard.html")
    try:
        with open(template_path, "r", encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>模板文件未找到: {template_path}</h1>")
