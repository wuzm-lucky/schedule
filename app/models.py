from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from .database import Base


class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    job_id = Column(String(100), index=True, comment='任务ID')
    job_name = Column(String(200), comment='任务名称')
    status = Column(String(20), comment='执行状态: success/failed/missed')
    run_time = Column(DateTime, comment='执行时间')
    duration = Column(Float, nullable=True, comment='耗时(秒)')
    result = Column(Text, nullable=True, comment='执行结果或异常堆栈')