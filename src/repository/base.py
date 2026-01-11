"""
Repository 基类
提供通用的 CRUD 操作
"""

from typing import Generic, TypeVar, List, Optional, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """通用仓储基类"""

    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    def get(self, id: Any) -> Optional[T]:
        """根据ID获取单条记录"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """根据字段值获取单条记录"""
        if not hasattr(self.model, field):
            return None
        return self.db.query(self.model).filter(
            getattr(self.model, field) == value
        ).first()

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[T]:
        """列表查询"""
        query = self.db.query(self.model)
        query = self._apply_filters(query, filters)
        return query.offset(skip).limit(limit).all()

    def list_all(self, **filters) -> List[T]:
        """获取所有符合条件的记录"""
        query = self.db.query(self.model)
        query = self._apply_filters(query, filters)
        return query.all()

    def count(self, **filters) -> int:
        """统计记录数"""
        query = self.db.query(func.count(self.model.id))
        query = self._apply_filters(query, filters)
        return query.scalar() or 0

    def create(self, obj: T) -> T:
        """创建记录"""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: T) -> T:
        """更新记录"""
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update_fields(self, id: Any, **fields) -> Optional[T]:
        """更新指定字段"""
        obj = self.get(id)
        if obj:
            for key, value in fields.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            self.db.commit()
            self.db.refresh(obj)
        return obj

    def delete(self, id: Any) -> bool:
        """物理删除"""
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    def soft_delete(self, id: Any) -> bool:
        """逻辑删除"""
        obj = self.get(id)
        if obj and hasattr(obj, 'deleted'):
            obj.deleted = True
            obj.enabled = False
            self.db.commit()
            return True
        return False

    def restore(self, id: Any) -> bool:
        """恢复已删除的记录"""
        obj = self.get(id)
        if obj and hasattr(obj, 'deleted'):
            obj.deleted = False
            obj.enabled = True
            self.db.commit()
            return True
        return False

    def search_by_field(self, field: str, keyword: str) -> List[T]:
        """模糊搜索"""
        if not hasattr(self.model, field):
            return []
        return self.db.query(self.model).filter(
            getattr(self.model, field).like(f"%{keyword}%")
        ).all()

    def _apply_filters(self, query, filters: dict):
        """应用过滤条件"""
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query

    def exists(self, id: Any) -> bool:
        """检查记录是否存在"""
        return self.db.query(self.model).filter(
            self.model.id == id
        ).first() is not None
