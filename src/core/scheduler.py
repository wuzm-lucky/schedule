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
from src.repository.task_repository import TaskRepository, TaskExecutionRepository

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
        # 使用 Repository 从数据库加载任务
        repo = TaskRepository(db)
        task_model = repo.get_active(task_id)
        if not task_model:
            logger.error(f"Task not found in database: {task_id}")
            return

        task = task_model.to_domain()

        execution_id = scheduler._generate_execution_id(task_id)
        start_time = datetime.now()
        task_executor = get_task_executor()

        # 使用 Repository 创建执行记录
        exec_repo = TaskExecutionRepository(db)
        execution = exec_repo.create_execution(execution_id, task.id, task.name)
        execution.status = TaskStatus.RUNNING.value

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

        exec_repo.update_execution(
            execution_id,
            end_time=end_time,
            duration=duration,
            exit_code=result.get("exit_code")
        )

        # 更新任务统计
        repo.increment_stats(task_id, success=result.get("success", False))

        if result.get("success"):
            exec_repo.update_execution(
                execution_id,
                status=TaskStatus.SUCCESS.value,
                output=result.get("stdout", "")
            )
            logger.info(f"Task executed successfully: {task_id}, duration: {duration:.2f}s")
        else:
            error_msg = result.get("error") or result.get("stderr") or "Unknown error"
            exec_repo.update_execution(
                execution_id,
                status=TaskStatus.FAILED.value,
                error=error_msg
            )
            logger.error(f"Task execution failed: {task_id}, error: {error_msg}")

    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Task execution wrapper error: {task_id}\n{error_detail}")

        # 尝试更新执行记录
        try:
            if execution:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds() if 'start_time' in locals() else 0

                exec_repo = TaskExecutionRepository(db)
                exec_repo.update_execution(
                    execution_id,
                    end_time=end_time,
                    duration=duration,
                    status=TaskStatus.FAILED.value,
                    error=error_detail
                )

                # 更新失败统计
                repo = TaskRepository(db)
                repo.increment_stats(task_id, success=False)

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
                url=settings.database_url,
                tablename='apscheduler_jobs'
            )
        }

        # 创建调度器实例
        self.scheduler = BackgroundScheduler(
            timezone=settings.timezone,
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

    def add_task(self, task: Task, save_to_db: bool = True, force_add: bool = False) -> bool:
        """
        添加任务到调度器

        Args:
            task: 任务对象（Task 领域模型或 TaskModel）
            save_to_db: 是否保存到数据库
            force_add: 是否强制添加（即使任务未启用）

        Returns:
            bool: 是否添加成功
        """
        import traceback
        try:
            # 如果传入的是 TaskModel，转换为 Task 领域模型
            if isinstance(task, TaskModel):
                task = task.to_domain()
            if save_to_db:
                # 使用 Repository 保存任务
                db = SessionLocal()
                try:
                    repo = TaskRepository(db)
                    task_model = TaskModel.from_domain(task)

                    # 检查是否已存在
                    existing = repo.get(task.id)
                    if existing:
                        # 更新现有任务，保留统计信息
                        task_model.run_count = existing.run_count
                        task_model.success_count = existing.success_count
                        task_model.failed_count = existing.failed_count
                        task_model.deleted = existing.deleted
                        # 更新字段
                        for key in ['name', 'script_path', 'trigger_type', 'cron_expression',
                                   'interval_seconds', 'scheduled_time', 'arguments', 'working_directory',
                                   'environment', 'timeout', 'enabled', 'description',
                                   'notification_enabled', 'notification_config']:
                            setattr(existing, key, getattr(task_model, key))
                        db.commit()
                    else:
                        # 新增任务
                        task_model.run_count = 0
                        task_model.success_count = 0
                        task_model.failed_count = 0
                        task_model.deleted = False
                        repo.create(task_model)

                    logger.info(f"Task saved to database: {task.id}")
                finally:
                    db.close()

            # 如果任务已存在，先移除
            if self.scheduler.get_job(task.id):
                self.remove_task(task.id, remove_from_db=False)

            # 只有当任务启用时才添加到调度器（或强制添加）
            if task.enabled or force_add:
                trigger = self._create_trigger(task)
                logger.info(f"Trigger created for task {task.id}: {trigger}")

                self.scheduler.add_job(
                    func=_execute_task_wrapper,
                    trigger=trigger,
                    id=task.id,
                    name=task.name,
                    args=[task.id],
                    max_instances=1,
                    replace_existing=True,
                    misfire_grace_time=300
                )

                logger.info(f"Task added to scheduler: {task.id} - {task.name}")
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
            return True
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        db = SessionLocal()
        try:
            repo = TaskRepository(db)

            # 检查任务是否在数据库中存在
            task = repo.get_active(task_id)
            if not task:
                logger.error(f"Task not found in database: {task_id}")
                return False

            # 尝试暂停调度器中的任务（如果存在）
            if self.scheduler.get_job(task_id):
                try:
                    self.scheduler.pause_job(task_id)
                    logger.info(f"Job paused in scheduler: {task_id}")
                except Exception as e:
                    logger.warning(f"Failed to pause job in scheduler (continuing with DB update): {e}")
            else:
                logger.info(f"Job not found in scheduler, only updating DB: {task_id}")

            # 更新数据库状态
            repo.toggle_status(task_id, enabled=False)
            logger.info(f"Task paused: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            return False
        finally:
            db.close()

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        db = SessionLocal()
        try:
            repo = TaskRepository(db)

            # 总是从数据库重新加载任务配置，确保使用最新参数
            task_model = repo.get_active(task_id)
            if not task_model:
                logger.error(f"Task not found in database: {task_id}")
                return False

            # 转换为领域模型
            task = task_model.to_domain()

            # 无论任务是否已在调度器中，先移除旧配置
            try:
                self.scheduler.remove_job(task_id)
            except:
                pass

            # 添加新配置到调度器（这里可能失败）
            result = self.add_task(task, save_to_db=False, force_add=True)
            if not result:
                logger.error(f"Failed to add task to scheduler: {task_id}")
                return False

            # 只有调度器操作成功后，才更新数据库
            repo.toggle_status(task_id, enabled=True)
            logger.info(f"Task resumed: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False
        finally:
            db.close()

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
            repo = TaskRepository(db)
            task_model = repo.get_active(task_id)
            return task_model.to_domain() if task_model else None
        finally:
            db.close()

    def list_tasks_from_db(self, include_deleted: bool = False) -> List[Task]:
        """从数据库获取所有任务"""
        db = SessionLocal()
        try:
            repo = TaskRepository(db)
            task_models = repo.list_with_filter(include_deleted=include_deleted)
            return [tm.to_domain() for tm in task_models]
        finally:
            db.close()

    def get_task_executions(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取任务执行记录"""
        db = SessionLocal()
        try:
            repo = TaskExecutionRepository(db)
            executions = repo.get_by_task(task_id, limit)
            return [e.to_dict() for e in executions]
        finally:
            db.close()

    def _create_trigger(self, task: Task):
        """根据任务配置创建触发器"""
        # 兼容处理：如果 trigger_type 是字符串，转换为枚举
        if isinstance(task.trigger_type, str):
            try:
                trigger_type = TriggerType(task.trigger_type.strip())
            except (ValueError, AttributeError) as e:
                logger.error(f"Invalid trigger_type '{task.trigger_type}': {e}")
                raise ValueError(f"Unsupported trigger type: {task.trigger_type}")
        else:
            trigger_type = task.trigger_type

        # 记录触发器类型和关键参数，便于调试
        logger.info(f"Creating trigger for task {task.id}: type={trigger_type} ({type(trigger_type)}), cron={task.cron_expression}, interval={task.interval_seconds}, scheduled={task.scheduled_time}")

        if trigger_type == TriggerType.CRON:
            if not task.cron_expression:
                raise ValueError(f"cron_expression is required for cron trigger, got: {task.cron_expression}")

            cron_expr = task.cron_expression.strip()
            fields = cron_expr.split()

            # 处理不同格式的 cron 表达式
            # 5 字段: 分 时 日 月 周 (标准 Unix cron)
            # 6 字段: 秒 分 时 日 月 周 (包含秒)
            if len(fields) == 6:
                # 6 字段格式，使用 CronTrigger 构造函数
                return CronTrigger(
                    second=fields[0],
                    minute=fields[1],
                    hour=fields[2],
                    day=fields[3],
                    month=fields[4],
                    day_of_week=fields[5],
                    timezone=settings.timezone
                )
            elif len(fields) == 5:
                # 5 字段标准格式，使用 from_crontab
                return CronTrigger.from_crontab(cron_expr, timezone=settings.timezone)
            else:
                raise ValueError(f"Invalid cron expression '{cron_expr}': expected 5 or 6 fields, got {len(fields)}")

        elif trigger_type == TriggerType.INTERVAL:
            if not task.interval_seconds or task.interval_seconds <= 0:
                raise ValueError(f"interval_seconds must be positive for interval trigger, got: {task.interval_seconds}")
            return IntervalTrigger(
                seconds=task.interval_seconds,
                timezone=settings.timezone
            )

        elif trigger_type == TriggerType.DATE:
            if not task.scheduled_time:
                raise ValueError(f"scheduled_time is required for date trigger, got: {task.scheduled_time}")
            return DateTrigger(
                run_date=task.scheduled_time,
                timezone=settings.timezone
            )

        raise ValueError(f"Unsupported trigger type: {trigger_type} (type: {type(trigger_type)}, expected TriggerType enum)")

    def _on_job_executed(self, event):
        """APScheduler 事件回调"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")

    def _generate_execution_id(self, task_id: str) -> str:
        """生成执行ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
        return f"{task_id}_{timestamp}"

    def _load_tasks_from_db(self):
        """从数据库加载任务并添加到调度器"""
        db = SessionLocal()
        try:
            repo = TaskRepository(db)
            task_models = repo.list_active()

            for task_model in task_models:
                task = task_model.to_domain()
                if task:
                    try:
                        if not self.scheduler.get_job(task.id):
                            trigger = self._create_trigger(task)
                            self.scheduler.add_job(
                                func=_execute_task_wrapper,
                                trigger=trigger,
                                id=task.id,
                                name=task.name,
                                args=[task.id],
                                max_instances=1,
                                replace_existing=False
                            )
                            logger.info(f"Loaded task from db: {task.id} - {task.name}")
                    except Exception as e:
                        logger.error(f"Failed to load task {task.id}: {e}")
        finally:
            db.close()


# 全局调度器实例
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
