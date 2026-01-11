"""
统一异常定义
"""


class ScheduleException(Exception):
    """基础异常类"""

    def __init__(self, message: str, code: str = 'error', status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class TaskNotFoundException(ScheduleException):
    """任务不存在异常"""

    def __init__(self, task_id: str = ''):
        message = f"任务不存在: {task_id}" if task_id else "任务不存在"
        super().__init__(message, code='task_not_found', status_code=404)


class TaskAlreadyExistsException(ScheduleException):
    """任务已存在异常"""

    def __init__(self, task_id: str):
        super().__init__(
            f"任务已存在: {task_id}",
            code='task_already_exists',
            status_code=409
        )


class ScriptNotFoundException(ScheduleException):
    """脚本不存在异常"""

    def __init__(self, path: str):
        super().__init__(
            f"脚本不存在: {path}",
            code='script_not_found',
            status_code=404
        )


class TaskExecutionException(ScheduleException):
    """任务执行异常"""

    def __init__(self, task_id: str, error: str):
        super().__init__(
            f"任务执行失败: {task_id} - {error}",
            code='task_execution_failed',
            status_code=500
        )


class TaskTimeoutException(ScheduleException):
    """任务超时异常"""

    def __init__(self, task_id: str, timeout: int):
        super().__init__(
            f"任务执行超时: {task_id} (超时时间: {timeout}秒)",
            code='task_timeout',
            status_code=408
        )


class ValidationException(ScheduleException):
    """参数验证异常"""

    def __init__(self, message: str):
        super().__init__(
            message,
            code='validation_error',
            status_code=400
        )


class DatabaseException(ScheduleException):
    """数据库操作异常"""

    def __init__(self, message: str):
        super().__init__(
            f"数据库操作失败: {message}",
            code='database_error',
            status_code=500
        )
