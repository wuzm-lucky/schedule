"""
任务执行记录业务逻辑层
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from config.database import SessionLocal
from src.repository.task_repository import TaskExecutionRepository


class ExecutionService:
    """任务执行记录业务逻辑服务"""

    @staticmethod
    def get_db():
        """获取数据库会话"""
        return SessionLocal()

    @staticmethod
    def get_task_executions(
        task_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取任务执行记录"""
        db = ExecutionService.get_db()
        try:
            repo = TaskExecutionRepository(db)
            executions = repo.get_by_task(task_id, limit, status)

            return [ExecutionService._to_dict(e) for e in executions]
        finally:
            db.close()

    @staticmethod
    def create_execution(
        execution_id: str,
        task_id: str,
        task_name: str
    ):
        """创建执行记录"""
        db = ExecutionService.get_db()
        try:
            repo = TaskExecutionRepository(db)
            return repo.create_execution(execution_id, task_id, task_name)
        finally:
            db.close()

    @staticmethod
    def update_execution(
        execution_id: str,
        status: str,
        end_time: Optional[datetime] = None,
        duration: Optional[float] = None,
        exit_code: Optional[int] = None,
        output: Optional[str] = None,
        error: Optional[str] = None
    ):
        """更新执行记录"""
        db = ExecutionService.get_db()
        try:
            repo = TaskExecutionRepository(db)
            return repo.update_execution(
                execution_id,
                status=status,
                end_time=end_time,
                duration=duration,
                exit_code=exit_code,
                output=output,
                error=error
            )
        finally:
            db.close()

    @staticmethod
    def _to_dict(execution) -> Dict[str, Any]:
        """执行记录转换为字典"""
        return {
            "id": execution.id,
            "task_id": execution.task_id,
            "task_name": execution.task_name,
            "status": execution.status,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "duration": execution.duration,
            "exit_code": execution.exit_code,
            "output": execution.output,
            "error": execution.error
        }
