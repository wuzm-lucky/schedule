from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import sys
import os
from contextlib import contextmanager
from typing import Callable, TypeVar, Any
from functools import wraps

# 为了在直接运行 main.py 时能找到 config，我们将项目根目录加入 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings

settings = get_settings()

# 创建引擎 - 使用新的 database_url 属性
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False
)
# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 基类
Base = declarative_base()


# 依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory():
    """获取会话工厂"""
    return SessionLocal


@contextmanager
def get_db_session():
    """
    数据库会话上下文管理器

    使用方式:
        with get_db_session() as db:
            tasks = db.query(TaskModel).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def with_db(func):
    """
    数据库操作装饰器 - 自动处理会话

    使用方式:
        @with_db
        def get_all_tasks():
            return db.query(TaskModel).all()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            # 将 db 作为第一个参数传入函数
            result = func(db, *args, **kwargs)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    return wrapper


class DatabaseHelper:
    """
    数据库操作辅助类

    提供便捷的数据库操作方法，自动处理会话管理
    """

    @staticmethod
    def query_one(model_class, **filters):
        """查询单条记录"""
        with get_db_session() as db:
            instance = db.query(model_class).filter_by(**filters).first()
            if instance:
                db.expunge(instance)  # 从会话中分离，使其可在会话关闭后访问
            return instance

    @staticmethod
    def query_all(model_class, **filters):
        """查询所有记录"""
        with get_db_session() as db:
            query = db.query(model_class)
            if filters:
                query = query.filter_by(**filters)
            results = query.all()
            for instance in results:
                db.expunge(instance)  # 从会话中分离所有对象
            return results

    @staticmethod
    def create(model_class, **kwargs):
        """创建新记录"""
        with get_db_session() as db:
            instance = model_class(**kwargs)
            db.add(instance)
            db.flush()  # 获取生成的ID
            db.expunge(instance)  # 从会话中分离，使其可在会话关闭后访问
            return instance

    @staticmethod
    def update(model_class, filters: dict, **kwargs):
        """更新记录"""
        with get_db_session() as db:
            instance = db.query(model_class).filter_by(**filters).first()
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                db.expunge(instance)  # 从会话中分离，使其可在会话关闭后访问
            return instance

    @staticmethod
    def delete(model_class, **filters):
        """删除记录"""
        with get_db_session() as db:
            instance = db.query(model_class).filter_by(**filters).first()
            if instance:
                db.delete(instance)
                return True
            return False

    @staticmethod
    def execute(func: Callable[[Session], Any]):
        """执行自定义数据库操作"""
        with get_db_session() as db:
            return func(db)


# 便捷导出
db = DatabaseHelper()


def init_db():
    """初始化数据库表"""
    from src.models.database import TaskModel, TaskExecutionModel
    Base.metadata.create_all(bind=engine)
