from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sys
import os

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


def init_db():
    """初始化数据库表"""
    from src.models.database import TaskModel, TaskExecutionModel
    Base.metadata.create_all(bind=engine)
