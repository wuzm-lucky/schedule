"""
任务调度器核心模块
基于 APScheduler 实现定时任务调度
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from config.database import SessionLocal
from src.core.task_executor import TaskExecutor
from src.models.task import Task, TaskStatus, TriggerType
from src.models.database import TaskModel, TaskExecutionModel

logger = logging.getLogger(__name__)
settings = get_settings()

# 全局任务执行器实例
_task_executor_instance = None


def get_task_executor() -> TaskExecutor:
    """获取任务执行器单例"""
    global _task_executor_instance
    if _task_executor_instance is None:
        _task_executor_instance = TaskExecutor()
    return _task_executor_instance


def _execute_task_wrapper(task_id: str):
    """
    任务执行包装器 - 模块级函数，避免序列化问题
    从数据库加载任务配置并执行
    """
    import traceback
    from src.core.scheduler import get_scheduler

    scheduler = get_scheduler()
    task = None
    execution = None
    db = SessionLocal()

    try:
        # 从数据库加载任务
        task = scheduler.get_task_from_db(task_id)
        if not task:
            logger.error(f"Task not found in database: {task_id}")
            return

        execution_id = scheduler._generate_execution_id(task_id)
        start_time = datetime.now()
        task_executor = get_task_executor()

        # 创建执行记录
        execution = TaskExecutionModel(
            id=execution_id,
            task_id=task.id,
            task_name=task.name,
            status=TaskStatus.RUNNING.value,
            start_time=start_time
        )

        db.add(execution)
        db.commit()

        # 记录任务开始
        scheduler._running_tasks[task.id] = {
            "execution_id": execution_id,
            "start_time": start_time,
            "status": TaskStatus.RUNNING
        }

        logger.info(f"Starting task execution: {task_id}, execution_id: {execution_id}")

        # 执行任务
        result = task_executor.execute(task, execution_id)

        # 更新执行记录
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        execution.end_time = end_time
        execution.duration = duration
        execution.exit_code = result.get("exit_code")

        # 更新任务运行次数
        task_model = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if task_model:
            task_model.run_count = (task_model.run_count or 0) + 1

        if result.get("success"):
            execution.status = TaskStatus.SUCCESS.value
            execution.output = result.get("stdout", "")
            if task_model:
                task_model.success_count = (task_model.success_count or 0) + 1
            logger.info(f"Task executed successfully: {task_id}, duration: {duration:.2f}s")
        else:
            execution.status = TaskStatus.FAILED.value
            error_msg = result.get("error") or result.get("stderr") or "Unknown error"
            execution.error = error_msg
            if task_model:
                task_model.failed_count = (task_model.failed_count or 0) + 1
            logger.error(f"Task execution failed: {task_id}, error: {error_msg}")

        db.commit()

    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Task execution wrapper error: {task_id}\n{error_detail}")

        # 尝试更新执行记录
        try:
            if execution:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds() if 'start_time' in locals() else 0

                execution.end_time = end_time
                execution.duration = duration
                execution.status = TaskStatus.FAILED.value
                execution.error = error_detail

                # 更新任务运行次数
                task_model = db.query(TaskModel).filter(TaskModel.id == task_id).first()
                if task_model:
                    task_model.run_count = (task_model.run_count or 0) + 1
                    task_model.failed_count = (task_model.failed_count or 0) + 1

                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update execution record: {db_error}")

    finally:
        if task_id:
            scheduler._running_tasks.pop(task_id, None)
        db.close()


class TaskScheduler:
    """任务调度器 - 支持数据库持久化"""

    def __init__(self):
        # 配置数据库 JobStore
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}",
                tablename='apscheduler_jobs'
            )
        }

        # 创建调度器实例
        self.scheduler = BackgroundScheduler(
            timezone=settings.TIMEZONE,
            jobstores=jobstores
        )
        self.task_executor = TaskExecutor()
        self._running_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> execution_info

        # 注册事件监听器
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            # 从数据库加载已保存的任务
            self._load_tasks_from_db()
            logger.info("任务调度器启动完成")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        self.scheduler.shutdown(wait=wait)
        logger.info("任务调度器关闭完成")

    def add_task(self, task: Task, save_to_db: bool = True) -> bool:
        """
        添加任务到调度器

        Args:
            task: 任务对象
            save_to_db: 是否保存到数据库

        Returns:
            bool: 是否添加成功
        """
        import traceback
        try:
            # 先保存任务配置到数据库（必须在 add_job 之前）
            if save_to_db:
                self._save_task_to_db(task)
                logger.info(f"Task saved to database: {task.id}")

            # 如果任务已存在，先移除
            if self.scheduler.get_job(task.id):
                self.remove_task(task.id, remove_from_db=False)

            # 只有当任务启用时才添加到调度器
            if task.enabled:
                # 创建触发器
                trigger = self._create_trigger(task)
                logger.info(f"Trigger created for task {task.id}: {trigger}")

                # 添加任务到调度器 - 只传递 task_id，避免序列化问题
                self.scheduler.add_job(
                    func=_execute_task_wrapper,  # 使用模块级函数
                    trigger=trigger,
                    id=task.id,
                    name=task.name,
                    args=[task.id],  # 只传递 task_id，执行时从数据库重新加载
                    max_instances=1,
                    replace_existing=True,
                    misfire_grace_time=300
                )

                logger.info(f"Task added to scheduler: {task.id} - {task.name}")
                return True
            else:
                logger.info(f"Task saved but not added to scheduler (disabled): {task.id} - {task.name}")
                return True

        except Exception as e:
            logger.error(f"Failed to add task {task.id}: {e}\n{traceback.format_exc()}")
            return False

    def remove_task(self, task_id: str, remove_from_db: bool = True) -> bool:
        """移除任务"""
        try:
            self.scheduler.remove_job(task_id)
            logger.info(f"Task removed: {task_id}")

            # 从数据库删除任务配置
            if remove_from_db:
                self._remove_task_from_db(task_id)

            return True
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(task_id)
            logger.info(f"Task paused: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            # 检查任务是否已在调度器中
            if not self.scheduler.get_job(task_id):
                # 如果任务不在调度器中，从数据库加载并添加
                task = self.get_task_from_db(task_id)
                if task:
                    # 添加任务到调度器
                    self.add_task(task, save_to_db=False)
                    logger.info(f"Task added to scheduler on resume: {task_id}")
                else:
                    logger.error(f"Task not found in database: {task_id}")
                    return False

            # 恢复任务执行
            self.scheduler.resume_job(task_id)
            logger.info(f"Task resumed: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False

    def get_next_run_time(self, task_id: str) -> Optional[datetime]:
        """获取任务下次执行时间"""
        job = self.scheduler.get_job(task_id)
        return job.next_run_time if job else None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return jobs

    def get_task_from_db(self, task_id: str) -> Optional[Task]:
        """从数据库获取任务配置"""
        db = SessionLocal()
        try:
            task_model = db.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task_model:
                return self._db_model_to_task(task_model)
            return None
        finally:
            db.close()

    def list_tasks_from_db(self, include_deleted: bool = False) -> List[Task]:
        """从数据库获取所有任务"""
        db = SessionLocal()
        try:
            query = db.query(TaskModel)
            if not include_deleted:
                query = query.filter(TaskModel.deleted == False)
            task_models = query.all()
            return [self._db_model_to_task(tm) for tm in task_models]
        finally:
            db.close()

    def get_task_executions(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取任务执行记录"""
        db = SessionLocal()
        try:
            executions = db.query(TaskExecutionModel).filter(
                TaskExecutionModel.task_id == task_id
            ).order_by(TaskExecutionModel.start_time.desc()).limit(limit).all()

            return [self._execution_to_dict(e) for e in executions]
        finally:
            db.close()

    def _create_trigger(self, task: Task):
        """根据任务配置创建触发器"""
        if task.trigger_type == TriggerType.CRON:
            return CronTrigger.from_crontab(task.cron_expression, timezone=settings.TIMEZONE)

        elif task.trigger_type == TriggerType.INTERVAL:
            return IntervalTrigger(
                seconds=task.interval_seconds,
                timezone=settings.TIMEZONE
            )

        elif task.trigger_type == TriggerType.DATE:
            return DateTrigger(
                run_date=task.scheduled_time,
                timezone=settings.TIMEZONE
            )

        raise ValueError(f"Unsupported trigger type: {task.trigger_type}")

    def _on_job_executed(self, event):
        """APScheduler 事件回调"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")

    def _generate_execution_id(self, task_id: str) -> str:
        """生成执行ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
        return f"{task_id}_{timestamp}"

    def _save_task_to_db(self, task: Task):
        """保存任务配置到数据库"""
        db = SessionLocal()
        try:
            # 检查是否已存在
            existing = db.query(TaskModel).filter(TaskModel.id == task.id).first()

            task_data = {
                "id": task.id,
                "name": task.name,
                "script_path": task.script_path,
                "trigger_type": task.trigger_type.value,
                "cron_expression": task.cron_expression,
                "interval_seconds": task.interval_seconds,
                "scheduled_time": task.scheduled_time,
                "arguments": json.dumps(task.arguments) if task.arguments else None,
                "working_directory": task.working_directory,
                "environment": json.dumps(task.environment) if task.environment else None,
                "timeout": task.timeout,
                "enabled": task.enabled,
                "description": task.description,
                "notification_enabled": task.notification.enabled if task.notification else False,
                "notification_config": json.dumps({
                    "channels": [c.value for c in task.notification.channels],
                    "on_success": task.notification.on_success,
                    "on_failure": task.notification.on_failure,
                    "config": task.notification.config
                }) if task.notification else None
            }

            if existing:
                # 更新 - 不覆盖 deleted 和 run_count
                for key, value in task_data.items():
                    setattr(existing, key, value)
            else:
                # 新增 - 添加 deleted=False
                task_data["deleted"] = False
                task_data["run_count"] = 0
                task_data["success_count"] = 0
                task_data["failed_count"] = 0
                db_task = TaskModel(**task_data)
                db.add(db_task)

            db.commit()
        except Exception as e:
            logger.error(f"Failed to save task to db: {e}")
            db.rollback()
        finally:
            db.close()

    def _remove_task_from_db(self, task_id: str):
        """从数据库删除任务配置"""
        db = SessionLocal()
        try:
            db.query(TaskModel).filter(TaskModel.id == task_id).delete()
            db.commit()
        except Exception as e:
            logger.error(f"Failed to remove task from db: {e}")
            db.rollback()
        finally:
            db.close()

    def _load_tasks_from_db(self):
        """从数据库加载任务并添加到调度器"""
        db = SessionLocal()
        try:
            # 只加载未删除且已启用的任务
            task_models = db.query(TaskModel).filter(
                TaskModel.enabled == True,
                TaskModel.deleted == False
            ).all()
            for task_model in task_models:
                task = self._db_model_to_task(task_model)
                if task:
                    # 添加到调度器但不重复保存到数据库
                    try:
                        if not self.scheduler.get_job(task.id):
                            trigger = self._create_trigger(task)
                            self.scheduler.add_job(
                                func=_execute_task_wrapper,  # 使用模块级函数
                                trigger=trigger,
                                id=task.id,
                                name=task.name,
                                args=[task.id],  # 只传递 task_id
                                max_instances=1,
                                replace_existing=False
                            )
                            logger.info(f"Loaded task from db: {task.id} - {task.name}")
                    except Exception as e:
                        logger.error(f"Failed to load task {task.id}: {e}")
        finally:
            db.close()

    def _db_model_to_task(self, task_model: TaskModel) -> Optional[Task]:
        """数据库模型转换为 Task 对象"""
        try:
            from src.models.task import TriggerType, NotificationConfig, NotificationChannel

            # 解析通知配置
            notification = None
            if task_model.notification_enabled and task_model.notification_config:
                notif_config = json.loads(task_model.notification_config)
                notification = NotificationConfig(
                    enabled=True,
                    channels=[NotificationChannel(c) for c in notif_config.get("channels", [])],
                    on_success=notif_config.get("on_success", False),
                    on_failure=notif_config.get("on_failure", True),
                    config=notif_config.get("config", {})
                )

            return Task(
                id=task_model.id,
                name=task_model.name,
                script_path=task_model.script_path,
                trigger_type=TriggerType(task_model.trigger_type),
                cron_expression=task_model.cron_expression,
                interval_seconds=task_model.interval_seconds,
                scheduled_time=task_model.scheduled_time,
                arguments=json.loads(task_model.arguments) if task_model.arguments else [],
                working_directory=task_model.working_directory,
                environment=json.loads(task_model.environment) if task_model.environment else {},
                timeout=task_model.timeout,
                enabled=task_model.enabled,
                description=task_model.description,
                notification=notification
            )
        except Exception as e:
            logger.error(f"Failed to convert db model to task: {e}")
            return None

    def _execution_to_dict(self, execution: TaskExecutionModel) -> Dict[str, Any]:
        """执行记录转换为字典"""
        return {
            "id": execution.id,
            "task_id": execution.task_id,
            "task_name": execution.task_name,
            "status": execution.status,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "duration": execution.duration,
            "exit_code": execution.exit_code,
            "output": execution.output,
            "error": execution.error
        }


# 全局调度器实例
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
