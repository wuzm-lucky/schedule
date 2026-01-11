"""
任务数据访问层
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.repository.base import BaseRepository
from src.models.database import TaskModel, TaskExecutionModel


class TaskRepository(BaseRepository[TaskModel]):
    """任务仓储"""

    def __init__(self, db: Session):
        super().__init__(TaskModel, db)

    def list_active(self) -> List[TaskModel]:
        """获取所有启用的任务"""
        return self.db.query(TaskModel).filter(
            TaskModel.enabled == True,
            TaskModel.deleted == False
        ).all()

    def list_with_filter(
        self,
        keyword: Optional[str] = None,
        enabled: Optional[bool] = None,
        include_deleted: bool = False
    ) -> List[TaskModel]:
        """带过滤条件的任务列表"""
        query = self.db.query(TaskModel)

        if not include_deleted:
            query = query.filter(TaskModel.deleted == False)

        if keyword:
            query = query.filter(TaskModel.name.like(f"%{keyword}%"))

        if enabled is not None:
            query = query.filter(TaskModel.enabled == enabled)

        return query.order_by(desc(TaskModel.created_at)).all()

    def get_active(self, task_id: str) -> Optional[TaskModel]:
        """获取启用的任务"""
        return self.db.query(TaskModel).filter(
            TaskModel.id == task_id,
            TaskModel.deleted == False
        ).first()

    def increment_stats(self, task_id: str, success: bool = True) -> bool:
        """更新任务统计"""
        task = self.get_active(task_id)
        if task:
            task.run_count = (task.run_count or 0) + 1
            if success:
                task.success_count = (task.success_count or 0) + 1
            else:
                task.failed_count = (task.failed_count or 0) + 1
            self.db.commit()
            return True
        return False

    def toggle_status(self, task_id: str, enabled: bool) -> bool:
        """切换任务状态"""
        task = self.get_active(task_id)
        if task:
            task.enabled = enabled
            self.db.commit()
            return True
        return False


class TaskExecutionRepository(BaseRepository[TaskExecutionModel]):
    """任务执行记录仓储"""

    def __init__(self, db: Session):
        super().__init__(TaskExecutionModel, db)

    def get_by_task(
        self,
        task_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[TaskExecutionModel]:
        """获取任务的执行记录"""
        query = self.db.query(TaskExecutionModel).filter(
            TaskExecutionModel.task_id == task_id
        )

        if status:
            query = query.filter(TaskExecutionModel.status == status)

        return query.order_by(
            desc(TaskExecutionModel.start_time)
        ).limit(limit).all()

    def create_execution(
        self,
        execution_id: str,
        task_id: str,
        task_name: str
    ) -> TaskExecutionModel:
        """创建执行记录"""
        from datetime import datetime
        execution = TaskExecutionModel(
            id=execution_id,
            task_id=task_id,
            task_name=task_name,
            status='running',
            start_time=datetime.now()
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def update_execution(
        self,
        execution_id: str,
        **fields
    ) -> Optional[TaskExecutionModel]:
        """更新执行记录"""
        execution = self.get(execution_id)
        if execution:
            for key, value in fields.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)
            self.db.commit()
            self.db.refresh(execution)
        return execution
