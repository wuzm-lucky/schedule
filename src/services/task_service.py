"""
任务业务逻辑层
"""

import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from config.database import SessionLocal
from src.models.task import Task, TriggerType, NotificationConfig, NotificationChannel
from src.models.database import TaskModel
from src.repository.task_repository import TaskRepository


class TaskService:
    """任务业务逻辑服务"""

    @staticmethod
    def get_db():
        """获取数据库会话"""
        return SessionLocal()

    @staticmethod
    def list_tasks(
        keyword: Optional[str] = None,
        enabled: Optional[bool] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """获取任务列表"""
        db = TaskService.get_db()
        try:
            repo = TaskRepository(db)
            tasks = repo.list_with_filter(keyword, enabled, include_deleted)

            # 获取下次执行时间
            from src.core.scheduler import get_scheduler
            scheduler = get_scheduler()

            result = []
            for task in tasks:
                next_run_time = scheduler.get_next_run_time(task.id)
                result.append({
                    "id": task.id,
                    "name": task.name,
                    "script_path": task.script_path,
                    "trigger_type": task.trigger_type,
                    "enabled": task.enabled,
                    "deleted": task.deleted,
                    "run_count": task.run_count,
                    "success_count": task.success_count,
                    "failed_count": task.failed_count,
                    "next_run_time": next_run_time.isoformat() if next_run_time else None,
                    "description": task.description,
                    "cron_expression": task.cron_expression,
                    "interval_seconds": task.interval_seconds,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None
                })
            return result
        finally:
            db.close()

    @staticmethod
    def get_task(task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        db = TaskService.get_db()
        try:
            repo = TaskRepository(db)
            task = repo.get_active(task_id)
            if not task:
                return None

            from src.core.scheduler import get_scheduler
            scheduler = get_scheduler()
            next_run_time = scheduler.get_next_run_time(task_id)

            return {
                "id": task.id,
                "name": task.name,
                "script_path": task.script_path,
                "trigger_type": task.trigger_type,
                "enabled": task.enabled,
                "deleted": task.deleted,
                "run_count": task.run_count,
                "success_count": task.success_count,
                "failed_count": task.failed_count,
                "next_run_time": next_run_time.isoformat() if next_run_time else None,
                "description": task.description,
                "cron_expression": task.cron_expression,
                "interval_seconds": task.interval_seconds,
                "arguments": json.loads(task.arguments) if task.arguments else [],
                "working_directory": task.working_directory,
                "timeout": task.timeout,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
        finally:
            db.close()

    @staticmethod
    def create_task(
        name: str,
        script_path: str,
        trigger_type: str,
        trigger_args: Optional[Dict] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        scheduled_time: Optional[datetime] = None,
        arguments: Optional[List[str]] = None,
        working_directory: Optional[str] = None,
        timeout: int = 300,
        enabled: bool = True,
        description: Optional[str] = None
    ) -> bool:
        """创建任务"""
        db = TaskService.get_db()
        try:
            # 构建触发参数
            if trigger_type == 'cron' and trigger_args and not cron_expression:
                hour = trigger_args.get("hour", "*")
                minute = trigger_args.get("minute", "*")
                second = trigger_args.get("second", "0")
                cron_expression = f"{second} {minute} {hour} * * *"
            elif trigger_type == 'interval' and not interval_seconds:
                interval_seconds = trigger_args.get("seconds", 60) if trigger_args else 60

            # 创建任务对象
            task_id = str(uuid.uuid4())
            task = Task(
                id=task_id,
                name=name,
                script_path=script_path,
                trigger_type=TriggerType(trigger_type),
                cron_expression=cron_expression,
                interval_seconds=interval_seconds,
                scheduled_time=scheduled_time,
                arguments=arguments or [],
                working_directory=working_directory,
                timeout=timeout,
                enabled=enabled,
                description=description
            )

            # 保存到数据库
            repo = TaskRepository(db)
            task_model = TaskModel.from_domain(task)
            repo.create(task_model)

            # 添加到调度器
            from src.core.scheduler import get_scheduler
            scheduler = get_scheduler()
            return scheduler.add_task(task, save_to_db=False)

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @staticmethod
    def update_task(
        task_id: str,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        description: Optional[str] = None,
        script_path: Optional[str] = None,
        trigger_type: Optional[str] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        scheduled_time: Optional[datetime] = None,
        arguments: Optional[List[str]] = None,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """更新任务"""
        db = TaskService.get_db()
        try:
            repo = TaskRepository(db)
            task = repo.get_active(task_id)
            if not task:
                return False

            # 检测触发参数是否发生变化
            trigger_changed = (
                (trigger_type is not None and trigger_type != task.trigger_type) or
                (cron_expression is not None and cron_expression != task.cron_expression) or
                (interval_seconds is not None and interval_seconds != task.interval_seconds) or
                (scheduled_time is not None)
            )

            # 更新字段
            update_fields = {}
            if name is not None:
                update_fields['name'] = name
            if description is not None:
                update_fields['description'] = description
            if script_path is not None:
                update_fields['script_path'] = script_path
            if trigger_type is not None:
                update_fields['trigger_type'] = trigger_type
            if cron_expression is not None:
                update_fields['cron_expression'] = cron_expression
            if interval_seconds is not None:
                update_fields['interval_seconds'] = interval_seconds
            if scheduled_time is not None:
                update_fields['scheduled_time'] = scheduled_time
            if arguments is not None:
                update_fields['arguments'] = json.dumps(arguments)
            if working_directory is not None:
                update_fields['working_directory'] = working_directory
            if timeout is not None:
                update_fields['timeout'] = timeout

            repo.update_fields(task_id, **update_fields)

            # 重新加载任务以获取最新状态
            task = repo.get_active(task_id)
            if not task:
                return False

            # 同步调度器状态
            from src.core.scheduler import get_scheduler
            scheduler = get_scheduler()

            # 如果触发参数变化了，需要重新添加到调度器
            if trigger_changed:
                # 先从调度器移除
                try:
                    scheduler.scheduler.remove_job(task_id)
                except:
                    pass

                # 如果任务当前是启用状态，重新添加
                if task.enabled:
                    domain_task = task.to_domain()
                    scheduler.add_task(domain_task, save_to_db=False, force_add=True)

            # 如果启用状态有变化，同步到调度器
            if enabled is not None:
                if enabled:
                    scheduler.resume_task(task_id)
                else:
                    scheduler.pause_task(task_id)

            return True
        finally:
            db.close()

    @staticmethod
    def delete_task(task_id: str) -> bool:
        """删除任务（逻辑删除）"""
        db = TaskService.get_db()
        try:
            repo = TaskRepository(db)

            # 从调度器移除
            from src.core.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.remove_task(task_id, remove_from_db=False)

            # 逻辑删除
            return repo.soft_delete(task_id)
        finally:
            db.close()

    @staticmethod
    def restore_task(task_id: str) -> bool:
        """恢复已删除的任务"""
        db = TaskService.get_db()
        try:
            repo = TaskRepository(db)
            result = repo.restore(task_id)

            if result:
                # 重新添加到调度器
                task = repo.get(task_id)
                if task:
                    from src.core.scheduler import get_scheduler
                    scheduler = get_scheduler()
                    domain_task = task.to_domain()
                    scheduler.add_task(domain_task, save_to_db=False)

            return result
        finally:
            db.close()

    @staticmethod
    def pause_task(task_id: str) -> bool:
        """暂停任务"""
        from src.core.scheduler import get_scheduler
        return get_scheduler().pause_task(task_id)

    @staticmethod
    def resume_task(task_id: str) -> bool:
        """恢复任务"""
        from src.core.scheduler import get_scheduler
        return get_scheduler().resume_task(task_id)

    @staticmethod
    def execute_task(task_id: str) -> bool:
        """立即执行任务"""
        from src.core.scheduler import get_scheduler, _execute_task
        import threading

        scheduler = get_scheduler()
        task = scheduler.get_task_from_db(task_id)
        if not task:
            return False

        # 异步执行
        def run():
            try:
                from src.core.scheduler import _execute_task_wrapper
                _execute_task_wrapper(task_id)
            except Exception as e:
                pass

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return True
