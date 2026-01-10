"""
任务调度器核心模块
基于 APScheduler 实现定时任务调度
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from src.core.task_executor import TaskExecutor
from src.models.task import Task, TaskStatus, TriggerType

logger = logging.getLogger(__name__)
settings = get_settings()


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
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
            logger.info("任务调度器启动完成")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        self.scheduler.shutdown(wait=wait)
        logger.info("任务调度器关闭完成")

    def add_task(self, task: Task) -> bool:
        """
        添加任务到调度器

        Args:
            task: 任务对象

        Returns:
            bool: 是否添加成功
        """
        try:
            # 如果任务已存在，先移除
            if self.scheduler.get_job(task.id):
                self.remove_task(task.id)

            # 创建触发器
            trigger = self._create_trigger(task)

            # 添加任务
            self.scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger,
                id=task.id,
                name=task.name,
                args=[task],
                max_instances=1,  # 同一任务同时只运行一个实例
                replace_existing=True,
                misfire_grace_time=300  # 错过执行时间的容忍度（秒）
            )

            logger.info(f"Task added: {task.id} - {task.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add task {task.id}: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        try:
            job = self.scheduler.remove_job(task_id)
            logger.info(f"Task removed: {task_id}")
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

    def _execute_task_wrapper(self, task: Task):
        """任务执行包装器"""
        execution_id = self._generate_execution_id(task.id)

        # 记录任务开始
        self._running_tasks[task.id] = {
            "execution_id": execution_id,
            "start_time": datetime.now(),
            "status": TaskStatus.RUNNING
        }

        try:
            # 执行任务
            self.task_executor.execute(task, execution_id)

        except Exception as e:
            logger.error(f"Task execution error: {task.id} - {e}")

        finally:
            self._running_tasks.pop(task.id, None)

    def _on_job_executed(self, event):
        """APScheduler 事件回调"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")

    def _generate_execution_id(self, task_id: str) -> str:
        """生成执行ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{task_id}_{timestamp}"


# 全局调度器实例
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
