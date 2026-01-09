import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from app.database import SessionLocal
from app.models import TaskLog
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import settings

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.WARNING)
# 配置 JobStore (持久化)
jobstores = {
    'default': SQLAlchemyJobStore(url=settings.SQLALCHEMY_DATABASE_URI)
}
# 配置执行器
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 30
}
# 初始化调度器实例
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone=settings.SCHEDULER_TIMEZONE
)


def job_listener(event):
    """监听任务执行事件"""
    db = SessionLocal()
    try:
        job = scheduler.get_job(event.job_id)
        job_name = job.name if job else "Unknown"
        log = TaskLog(
            job_id=event.job_id,
            job_name=job_name,
            run_time=event.scheduled_run_time
        )
        if event.exception:
            log.status = 'failed'
            log.result = str(event.exception)
        elif event.code == EVENT_JOB_MISSED:
            log.status = 'missed'
            log.result = "Task missed"
        else:
            log.status = 'success'
            log.result = str(event.retval) if event.retval else "Finished successfully"
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Error logging task: {e}")
        db.rollback()
    finally:
        db.close()


# 添加监听器
scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)