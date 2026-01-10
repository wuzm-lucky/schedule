"""
SQLAlchemy ORM 模型定义
用于数据库持久化操作
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Float, Index
from sqlalchemy.orm import relationship
from config.database import Base


class TaskModel(Base):
    """任务配置表模型"""
    __tablename__ = "tasks"

    id = Column(String(191), primary_key=True, comment='任务ID')
    name = Column(String(200), nullable=False, comment='任务名称')
    script_path = Column(String(500), nullable=False, comment='脚本路径')
    trigger_type = Column(String(20), nullable=False, comment='触发器类型')
    cron_expression = Column(String(100), nullable=True, comment='Cron表达式')
    interval_seconds = Column(Integer, nullable=True, comment='间隔秒数')
    scheduled_time = Column(DateTime, nullable=True, comment='指定执行时间')
    arguments = Column(Text, nullable=True, comment='脚本参数(JSON)')
    working_directory = Column(String(500), nullable=True, comment='工作目录')
    environment = Column(Text, nullable=True, comment='环境变量(JSON)')
    timeout = Column(Integer, default=300, comment='超时时间(秒)')
    enabled = Column(Boolean, default=True, comment='是否启用')
    description = Column(Text, nullable=True, comment='任务描述')
    notification_enabled = Column(Boolean, default=False, comment='是否启用通知')
    notification_config = Column(Text, nullable=True, comment='通知配置(JSON)')
    run_count = Column(Integer, default=0, comment='运行次数')
    success_count = Column(Integer, default=0, comment='成功次数')
    failed_count = Column(Integer, default=0, comment='失败次数')
    deleted = Column(Boolean, default=False, comment='是否删除(逻辑删除)')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_enabled', 'enabled'),
        Index('idx_deleted', 'deleted'),
        Index('idx_trigger_type', 'trigger_type'),
        {'comment': '任务配置表'}
    )


class TaskExecutionModel(Base):
    """任务执行记录表模型"""
    __tablename__ = "task_executions"

    id = Column(String(191), primary_key=True, comment='执行ID')
    task_id = Column(String(191), nullable=False, comment='任务ID')
    task_name = Column(String(200), nullable=True, comment='任务名称')
    status = Column(String(20), nullable=False, comment='执行状态')
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, nullable=True, comment='结束时间')
    duration = Column(Float, nullable=True, comment='耗时(秒)')
    exit_code = Column(Integer, nullable=True, comment='退出码')
    output = Column(Text, nullable=True, comment='标准输出')
    error = Column(Text, nullable=True, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_status', 'status'),
        Index('idx_start_time', 'start_time'),
        {'comment': '任务执行记录表'}
    )
