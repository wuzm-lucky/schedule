"""
统一异常定义
提供结构化的错误处理机制
"""

from typing import Optional, Any, Dict


class ScheduleException(Exception):
    """基础异常类"""

    def __init__(self, message: str, code: str = 'error', status_code: int = 400, details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class TaskNotFoundException(ScheduleException):
    """任务不存在异常"""

    def __init__(self, task_id: str = ''):
        message = f"任务不存在: {task_id}" if task_id else "任务不存在"
        super().__init__(
            message,
            code='task_not_found',
            status_code=404,
            details={"task_id": task_id} if task_id else {}
        )


class TaskAlreadyExistsException(ScheduleException):
    """任务已存在异常"""

    def __init__(self, task_id: str):
        super().__init__(
            f"任务已存在: {task_id}",
            code='task_already_exists',
            status_code=409,
            details={"task_id": task_id}
        )


class TaskValidationException(ScheduleException):
    """任务参数验证异常"""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message,
            code='task_validation_error',
            status_code=400,
            details=details
        )


class ScriptNotFoundException(ScheduleException):
    """脚本不存在异常"""

    def __init__(self, path: str):
        super().__init__(
            f"脚本不存在: {path}",
            code='script_not_found',
            status_code=404,
            details={"script_path": path}
        )


class ExecutableNotFoundException(ScheduleException):
    """可执行文件未找到异常"""

    def __init__(self, executable: str, extension: str):
        super().__init__(
            f"未找到可执行文件: {executable} (用于.{extension}文件)",
            code='executable_not_found',
            status_code=500,
            details={"executable": executable, "extension": extension}
        )


class TaskExecutionException(ScheduleException):
    """任务执行异常"""

    def __init__(self, task_id: str, error: str, exit_code: Optional[int] = None):
        details = {"task_id": task_id, "reason": error}
        if exit_code is not None:
            details["exit_code"] = exit_code

        super().__init__(
            f"任务执行失败: {task_id} - {error}",
            code='task_execution_failed',
            status_code=500,
            details=details
        )


class TaskTimeoutException(ScheduleException):
    """任务超时异常"""

    def __init__(self, task_id: str, timeout: int):
        super().__init__(
            f"任务执行超时: {task_id} (超时时间: {timeout}秒)",
            code='task_timeout',
            status_code=408,
            details={"task_id": task_id, "timeout": timeout}
        )


class ValidationException(ScheduleException):
    """参数验证异常"""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message,
            code='validation_error',
            status_code=400,
            details=details
        )


class DatabaseException(ScheduleException):
    """数据库操作异常"""

    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(
            f"数据库操作失败: {message}",
            code='database_error',
            status_code=500,
            details=details
        )


class TriggerValidationException(ScheduleException):
    """触发器配置验证异常"""

    def __init__(self, trigger_type: str, reason: str):
        super().__init__(
            f"无效的{trigger_type}触发器配置: {reason}",
            code='trigger_validation_error',
            status_code=400,
            details={"trigger_type": trigger_type, "reason": reason}
        )


class CronExpressionException(TriggerValidationException):
    """Cron表达式异常"""

    def __init__(self, cron_expression: str, reason: str):
        super().__init__("cron", reason)
        self.message = f"无效的cron表达式 '{cron_expression}': {reason}"
        self.details["cron_expression"] = cron_expression
