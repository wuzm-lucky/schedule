"""
任务数据模型定义
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class TriggerType(Enum):
    """触发器类型"""
    CRON = "cron"           # Cron 表达式
    INTERVAL = "interval"   # 固定间隔
    DATE = "date"           # 指定日期时间


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 运行中
    SUCCESS = "success"     # 执行成功
    FAILED = "failed"       # 执行失败
    TIMEOUT = "timeout"     # 执行超时
    CANCELLED = "cancelled" # 已取消


class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    WECHAT_WORK = "wechat_work"    # 企业微信
    DINGTALK = "dingtalk"           # 钉钉
    WECHAT = "wechat"               # 微信（Server酱）
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = False
    channels: List[NotificationChannel] = field(default_factory=list)
    on_success: bool = False   # 成功时通知
    on_failure: bool = True    # 失败时通知
    config: Dict[str, Any] = field(default_factory=dict)  # 各渠道配置


@dataclass
class Task:
    """任务模型"""
    id: str
    name: str
    script_path: str                    # 脚本路径
    trigger_type: TriggerType           # 触发器类型

    # Cron 触发器参数
    cron_expression: Optional[str] = None  # 如 "0 15 * * *" 每天下午3点

    # 间隔触发器参数
    interval_seconds: Optional[int] = None  # 间隔秒数

    # 日期触发器参数
    scheduled_time: Optional[datetime] = None

    # 执行参数
    arguments: List[str] = field(default_factory=list)
    working_directory: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300                    # 超时时间（秒）

    # 状态
    enabled: bool = True
    description: Optional[str] = None

    # 通知配置
    notification: Optional[NotificationConfig] = None

    # 元数据
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.notification is None:
            self.notification = NotificationConfig()
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "script_path": self.script_path,
            "trigger_type": self.trigger_type.value,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "arguments": self.arguments,
            "working_directory": self.working_directory,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "description": self.description,
            "notification": {
                "enabled": self.notification.enabled,
                "channels": [c.value for c in self.notification.channels],
                "on_success": self.notification.on_success,
                "on_failure": self.notification.on_failure,
                "config": self.notification.config
            } if self.notification else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建任务"""
        notification = None
        if data.get("notification"):
            notif_data = data["notification"]
            notification = NotificationConfig(
                enabled=notif_data.get("enabled", False),
                channels=[NotificationChannel(c) for c in notif_data.get("channels", [])],
                on_success=notif_data.get("on_success", False),
                on_failure=notif_data.get("on_failure", True),
                config=notif_data.get("config", {})
            )

        return cls(
            id=data["id"],
            name=data["name"],
            script_path=data["script_path"],
            trigger_type=TriggerType(data["trigger_type"]),
            cron_expression=data.get("cron_expression"),
            interval_seconds=data.get("interval_seconds"),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]) if data.get("scheduled_time") else None,
            arguments=data.get("arguments", []),
            working_directory=data.get("working_directory"),
            environment=data.get("environment", {}),
            timeout=data.get("timeout", 300),
            enabled=data.get("enabled", True),
            description=data.get("description"),
            notification=notification
        )


@dataclass
class TaskExecution:
    """任务执行记录"""
    id: str                    # 执行ID
    task_id: str               # 任务ID
    task_name: str             # 任务名称
    status: TaskStatus         # 执行状态
    start_time: datetime       # 开始时间
    end_time: Optional[datetime] = None    # 结束时间
    exit_code: Optional[int] = None        # 退出码
    output: Optional[str] = None           # 输出内容
    error: Optional[str] = None            # 错误信息

    @property
    def duration(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error
        }
