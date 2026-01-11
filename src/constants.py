"""
全局常量定义
集中管理系统中使用的各种常量，避免魔法数字和字符串散布在代码中
"""

from enum import Enum


class SchedulerConfig:
    """调度器配置常量"""
    # 任务最大并发实例数
    MAX_INSTANCES = 1
    # 错过执行后的宽限时间（秒）
    MISFIRE_GRACE_TIME = 300
    # 默认任务超时时间（秒）
    DEFAULT_TIMEOUT = 300
    # 任务默认超时时间（秒）- 另一个常用值
    JOB_DEFAULT_TIMEOUT = 3600


class DatabaseConfig:
    """数据库配置常量"""
    # MySQL 字符串字段最大长度（utf8mb4 编码限制）
    MAX_STRING_LENGTH = 191
    # 任务ID长度
    TASK_ID_LENGTH = 36
    # 执行ID长度
    EXECUTION_ID_LENGTH = 64


class ValidationConfig:
    """验证配置常量"""
    # 任务名称最小/最大长度
    TASK_NAME_MIN_LENGTH = 1
    TASK_NAME_MAX_LENGTH = 100
    # 描述最大长度
    DESCRIPTION_MAX_LENGTH = 500
    # 脚本路径最大长度
    SCRIPT_PATH_MAX_LENGTH = 500
    # cron表达式最大长度
    CRON_EXPRESSION_MAX_LENGTH = 100


class LogConfig:
    """日志配置常量"""
    # 日志格式
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # 详细日志格式
    DETAIL_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    # 日期格式
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ScriptConfig:
    """脚本配置常量"""
    # 支持的脚本扩展名
    SUPPORTED_EXTENSIONS = {
        '.py',      # Python
        '.sh',      # Shell
        '.bash',    # Bash
        '.bat',     # Windows Batch
        '.cmd',     # Windows Command
        '.js',      # JavaScript (Node.js)
        '.ts',      # TypeScript (ts-node)
        '.ps1',     # PowerShell
        '.rb',      # Ruby
        '.php',     # PHP
        '.pl',      # Perl
    }

    # 脚本执行命令映射（跨平台兼容）
    # 使用 None 表示需要在运行时检测
    EXECUTABLE_MAP = {
        '.py': ['python'],  # 使用 sys.executable 在运行时替换
        '.sh': ['bash'],
        '.bash': ['bash'],
        '.bat': ['cmd.exe', '/c'],
        '.cmd': ['cmd.exe', '/c'],
        '.js': ['node'],
        '.ts': ['npx', 'ts-node'],
        '.ps1': ['pwsh', '-File'],
        '.rb': ['ruby'],
        '.php': ['php'],
        '.pl': ['perl'],
    }


class ExecutionStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class NotificationChannel(str, Enum):
    """通知渠道类型"""
    WEBHOOK = "webhook"
    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    FEISHU = "feishu"
