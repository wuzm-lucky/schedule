"""
任务管理接口 - 重构版
使用 Service 层处理业务逻辑
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

from config import get_settings
from src.constants import ValidationConfig
from src.services import TaskService, ExecutionService
from src.models import CommonResponse

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
    args: list = []

    # 完整格式（可选）
    id: Optional[str] = None
    script_path: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    scheduled_time: Optional[str] = None
    arguments: list = []
    working_directory: Optional[str] = None
    environment: dict = {}
    timeout: int = 300
    enabled: bool = True
    description: Optional[str] = None

    @field_validator('task_name')
    @classmethod
    def validate_task_name(cls, v: str) -> str:
        """验证任务名称"""
        if not (ValidationConfig.TASK_NAME_MIN_LENGTH <= len(v) <= ValidationConfig.TASK_NAME_MAX_LENGTH):
            raise ValueError(
                f'任务名称长度必须在{ValidationConfig.TASK_NAME_MIN_LENGTH}-'
                f'{ValidationConfig.TASK_NAME_MAX_LENGTH}之间'
            )
        return v.strip()

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """验证描述长度"""
        if v and len(v) > ValidationConfig.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f'描述长度不能超过{ValidationConfig.DESCRIPTION_MAX_LENGTH}字符')
        return v

    @field_validator('script_path', 'func_name')
    @classmethod
    def validate_script_path(cls, v: Optional[str]) -> Optional[str]:
        """验证脚本路径"""
        if v:
            v = v.strip()
            if len(v) > ValidationConfig.SCRIPT_PATH_MAX_LENGTH:
                raise ValueError(f'脚本路径长度不能超过{ValidationConfig.SCRIPT_PATH_MAX_LENGTH}字符')
        return v

    @field_validator('cron_expression')
    @classmethod
    def validate_cron_expression(cls, v: Optional[str]) -> Optional[str]:
        """验证cron表达式格式"""
        if v:
            v = v.strip()
            if len(v) > ValidationConfig.CRON_EXPRESSION_MAX_LENGTH:
                raise ValueError(f'cron表达式长度不能超过{ValidationConfig.CRON_EXPRESSION_MAX_LENGTH}字符')
            # 基本格式验证: 5或6个字段，用空格分隔
            fields = v.split()
            if len(fields) not in (5, 6):
                raise ValueError('cron表达式必须是5或6个字段（秒 分 时 日 月 周 或 分 时 日 月 周）')
        return v

    @field_validator('interval_seconds')
    @classmethod
    def validate_interval_seconds(cls, v: Optional[int]) -> Optional[int]:
        """验证间隔秒数"""
        if v is not None and v <= 0:
            raise ValueError('间隔秒数必须大于0')
        return v

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """验证超时时间"""
        if v < 1:
            raise ValueError('超时时间必须大于0秒')
        if v > 86400:  # 24小时
            raise ValueError('超时时间不能超过24小时（86400秒）')
        return v

    @field_validator('trigger_type')
    @classmethod
    def validate_trigger_type(cls, v: str) -> str:
        """验证触发器类型"""
        valid_types = {'cron', 'interval', 'date'}
        if v.lower() not in valid_types:
            raise ValueError(f'触发器类型必须是以下之一: {", ".join(valid_types)}')
        return v.lower()


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    script_path: Optional[str] = None
    trigger_type: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    scheduled_time: Optional[str] = None
    arguments: list = []
    working_directory: Optional[str] = None
    timeout: Optional[int] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """验证任务名称"""
        if v:
            v = v.strip()
            if not (ValidationConfig.TASK_NAME_MIN_LENGTH <= len(v) <= ValidationConfig.TASK_NAME_MAX_LENGTH):
                raise ValueError(
                    f'任务名称长度必须在{ValidationConfig.TASK_NAME_MIN_LENGTH}-'
                    f'{ValidationConfig.TASK_NAME_MAX_LENGTH}之间'
                )
        return v

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """验证超时时间"""
        if v is not None:
            if v < 1:
                raise ValueError('超时时间必须大于0秒')
            if v > 86400:
                raise ValueError('超时时间不能超过24小时（86400秒）')
        return v


class TaskExecuteRequest(BaseModel):
    """立即执行任务请求"""
    task_id: str

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """验证任务ID格式"""
        if not v or not v.strip():
            raise ValueError('任务ID不能为空')
        return v.strip()


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
    try:
        tasks = TaskService.list_tasks(keyword, enabled, include_deleted)
        return CommonResponse(data=tasks)
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/query", response_model=CommonResponse)
async def query_tasks(query: TaskQueryRequest):
    """查询任务"""
    try:
        tasks = TaskService.list_tasks(query.keyword, query.enabled)
        return CommonResponse(data=tasks)
    except Exception as e:
        logger.error(f"查询任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=CommonResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    try:
        task = TaskService.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return CommonResponse(data=task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scripts", response_model=CommonResponse)
async def list_scripts():
    """获取 scripts 目录中的所有脚本文件"""
    scripts_dir = settings.scripts_path

    if not scripts_dir.exists():
        return CommonResponse(
            data=[],
            code='not_found',
            message='脚本目录不存在'
        )

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
async def add_task(request: TaskAddRequest):
    """添加新任务"""
    try:
        from datetime import datetime

        scheduled_time = None
        if request.trigger_type == 'date' and request.trigger_args and request.trigger_args.get("run_date"):
            scheduled_time = datetime.fromisoformat(request.trigger_args["run_date"])

        success = TaskService.create_task(
            name=request.task_name,
            script_path=request.script_path or request.func_name,
            trigger_type=request.trigger_type,
            trigger_args=request.trigger_args,
            cron_expression=request.cron_expression,
            interval_seconds=request.interval_seconds,
            scheduled_time=scheduled_time,
            arguments=request.arguments or request.args,
            working_directory=request.working_directory,
            timeout=request.timeout,
            enabled=request.enabled,
            description=request.description
        )

        if success:
            return CommonResponse(message="任务添加成功")
        else:
            raise HTTPException(status_code=500, detail="任务添加失败")

    except Exception as e:
        logger.error(f"添加任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tasks/{task_id}", response_model=CommonResponse)
async def update_task(task_id: str, request: TaskUpdateRequest):
    """更新任务"""
    try:
        from datetime import datetime
        import json

        # 处理 scheduled_time 字符串转换为 datetime
        scheduled_time = None
        if request.scheduled_time:
            try:
                scheduled_time = datetime.fromisoformat(request.scheduled_time.replace('Z', '+00:00'))
            except:
                pass

        success = TaskService.update_task(
            task_id=task_id,
            name=request.name,
            enabled=request.enabled,
            description=request.description,
            script_path=request.script_path,
            trigger_type=request.trigger_type,
            cron_expression=request.cron_expression,
            interval_seconds=request.interval_seconds,
            scheduled_time=scheduled_time,
            arguments=request.arguments,
            working_directory=request.working_directory,
            timeout=request.timeout
        )

        if success:
            return CommonResponse(message="任务更新成功")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}", response_model=CommonResponse)
async def remove_task(task_id: str):
    """删除任务（逻辑删除）"""
    try:
        success = TaskService.delete_task(task_id)
        if success:
            return CommonResponse(message="任务删除成功")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/restore", response_model=CommonResponse)
async def restore_task(task_id: str):
    """恢复已删除的任务"""
    try:
        success = TaskService.restore_task(task_id)
        if success:
            return CommonResponse(message="任务恢复成功")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/pause", response_model=CommonResponse)
async def pause_task(task_id: str):
    """暂停任务"""
    try:
        success = TaskService.pause_task(task_id)
        if success:
            return CommonResponse(message="任务暂停成功")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/resume", response_model=CommonResponse)
async def resume_task(task_id: str):
    """恢复任务"""
    try:
        success = TaskService.resume_task(task_id)
        if success:
            return CommonResponse(message="任务恢复成功")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/execute", response_model=CommonResponse)
async def execute_task_now(request: TaskExecuteRequest):
    """立即执行任务"""
    try:
        success = TaskService.execute_task(request.task_id)
        if success:
            return CommonResponse(message="任务已触发执行")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/run/{task_id}", response_model=CommonResponse)
async def run_task(task_id: str):
    """立即执行任务（前端路径兼容）"""
    return await execute_task_now(TaskExecuteRequest(task_id=task_id))


@router.get("/tasks/{task_id}/executions", response_model=CommonResponse)
async def get_task_executions(
    task_id: str,
    limit: int = Query(100, le=100),
    status: Optional[str] = None
):
    """获取任务执行记录"""
    try:
        executions = ExecutionService.get_task_executions(task_id, limit, status)
        return CommonResponse(data=executions)
    except Exception as e:
        logger.error(f"获取执行记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """管理后台页面"""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(BASE_DIR, "templates", "dashboard.html")
    try:
        with open(template_path, "r", encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>模板文件未找到: {template_path}</h1>")
