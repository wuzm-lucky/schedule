"""
SQLAlchemy ORM 模型定义
用于数据库持久化操作
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "script_path": self.script_path,
            "trigger_type": self.trigger_type,
            "enabled": self.enabled,
            "deleted": self.deleted,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "description": self.description,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "arguments": json.loads(self.arguments) if self.arguments else [],
            "working_directory": self.working_directory,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def to_domain(self):
        """转换为领域模型"""
        from src.models.task import Task, TriggerType, NotificationConfig, NotificationChannel

        # 安全地转换 trigger_type
        try:
            trigger_type_value = self.trigger_type.strip() if self.trigger_type else self.trigger_type
            trigger_type = TriggerType(trigger_type_value)
        except (ValueError, AttributeError) as e:
            # 如果转换失败，尝试通过值查找
            for t in TriggerType:
                if t.value == self.trigger_type:
                    trigger_type = t
                    break
            else:
                # 如果还是找不到，使用默认值
                import logging
                logging.error(f"Invalid trigger_type '{self.trigger_type}' for task {self.id}, defaulting to INTERVAL")
                trigger_type = TriggerType.INTERVAL

        notification = None
        if self.notification_enabled and self.notification_config:
            notif_config = json.loads(self.notification_config)
            notification = NotificationConfig(
                enabled=True,
                channels=[NotificationChannel(c) for c in notif_config.get("channels", [])],
                on_success=notif_config.get("on_success", False),
                on_failure=notif_config.get("on_failure", True),
                config=notif_config.get("config", {})
            )

        return Task(
            id=self.id,
            name=self.name,
            script_path=self.script_path,
            trigger_type=trigger_type,
            cron_expression=self.cron_expression,
            interval_seconds=self.interval_seconds,
            scheduled_time=self.scheduled_time,
            arguments=json.loads(self.arguments) if self.arguments else [],
            working_directory=self.working_directory,
            environment=json.loads(self.environment) if self.environment else {},
            timeout=self.timeout,
            enabled=self.enabled,
            description=self.description,
            notification=notification
        )

    @classmethod
    def from_domain(cls, task) -> 'TaskModel':
        """从领域模型创建"""
        return cls(
            id=task.id,
            name=task.name,
            script_path=task.script_path,
            trigger_type=task.trigger_type.value,
            cron_expression=task.cron_expression,
            interval_seconds=task.interval_seconds,
            scheduled_time=task.scheduled_time,
            arguments=json.dumps(task.arguments) if task.arguments else None,
            working_directory=task.working_directory,
            environment=json.dumps(task.environment) if task.environment else None,
            timeout=task.timeout,
            enabled=task.enabled,
            description=task.description,
            notification_enabled=task.notification.enabled if task.notification else False,
            notification_config=json.dumps({
                "channels": [c.value for c in task.notification.channels],
                "on_success": task.notification.on_success,
                "on_failure": task.notification.on_failure,
                "config": task.notification.config
            }) if task.notification else None
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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error
        }
