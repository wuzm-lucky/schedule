import os
import sys
from typing import Optional, Dict, Any

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# 确保能找到上级模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import get_db
from app.models import TaskLog
from app.scheduler.manager import scheduler
from app.scheduler.jobs import get_job_func
from app.scheduler import jobs  # 导入 jobs 模块

router = APIRouter()


class TaskCreate(BaseModel):
    name: str
    func_name: str
    trigger_type: str
    trigger_args: Dict[str, Any]
    args: Optional[list] = []


@router.post("/api/tasks")
async def add_task(task: TaskCreate, db: Session = Depends(get_db)):
    try:
        func = get_job_func(task.func_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    trigger = None
    if task.trigger_type == 'cron':
        trigger = CronTrigger(**task.trigger_args)
    elif task.trigger_type == 'interval':
        trigger = IntervalTrigger(**task.trigger_args)
    elif task.trigger_type == 'date':
        trigger = DateTrigger(**task.trigger_args)
    else:
        raise HTTPException(status_code=400, detail="Invalid trigger type")
    try:
        import datetime
        job_id = f"{task.func_name}_{int(datetime.datetime.now().timestamp())}"
        job_args = task.args
        if not job_args:
            job_args = [job_id]
        job = scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            name=task.name,
            args=job_args
        )
        return {"code": 0, "msg": "任务添加成功", "job_id": job.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/tasks/list")
async def get_task_list():
    """
    获取最新的可用脚本列表（触发热加载）
    """
    try:
        # 调用热加载刷新函数
        tasks = jobs.refresh_scripts()
        return {
            "code": 0,
            "data": tasks,
            "message": f"已加载 {len(tasks)} 个任务函数"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/tasks/{job_id}")
async def remove_task(job_id: str):
    scheduler.remove_job(job_id)
    return {"code": 0, "msg": "任务已删除"}


@router.post("/api/tasks/trigger/{job_id}")
async def trigger_task(job_id: str):
    try:
        scheduler.run_job(job_id)
        return {"code": 0, "msg": "任务已触发执行"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/tasks")
async def list_tasks():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None,
            "func_name": job.func_ref
        })
    return {"code": 0, "data": jobs}


@router.get("/api/logs")
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(TaskLog).order_by(TaskLog.run_time.desc()).limit(limit).all()
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "job_name": log.job_name,
            "status": log.status,
            "run_time": log.run_time.strftime("%Y-%m-%d %H:%M:%S"),
            "result": log.result
        })
    return {"code": 0, "data": result}


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