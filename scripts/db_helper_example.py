"""
数据库操作便捷用法示例
展示如何使用封装后的数据库操作方法和日志工具
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入日志工具 - 一行代码搞定日志配置
from src.utils.logger import get_script_logger, log_info, log_error

# 导入数据库模块
from config.database import get_db_session, with_db, db
from src.models.database import TaskModel, TaskExecutionModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

# 获取日志器
logger = get_script_logger()


# ==================== 方法1: 使用上下文管理器 ====================
def example_context_manager():
    """使用 with 语句自动管理会话"""
    logger.info("=== 方法1: 上下文管理器 ===")

    with get_db_session() as db:
        # 查询所有启用的任务
        tasks = db.query(TaskModel).filter(
            TaskModel.deleted == False,
            TaskModel.enabled == True
        ).all()

        logger.info(f"找到 {len(tasks)} 个启用的任务")
        for task in tasks[:3]:  # 只显示前3个
            logger.info(f"  - {task.name}")

    # 会自动提交和关闭，即使发生异常也会回滚


# ==================== 方法2: 使用装饰器 ====================
@with_db
def example_decorator(db: Session):
    """使用装饰器自动注入 db 会话"""
    logger.info("=== 方法2: 装饰器 ===")

    task = db.query(TaskModel).filter(
        TaskModel.deleted == False
    ).first()

    if task:
        logger.info(f"第一个任务: {task.name}")
        return task
    return None


# ==================== 方法3: 使用 DatabaseHelper 辅助类 ====================
def example_helper_class():
    """使用 DatabaseHelper 简化操作"""
    logger.info("=== 方法3: DatabaseHelper 辅助类 ===")

    # 查询单条记录
    task = db.query_one(TaskModel, deleted=False)
    if task:
        logger.info(f"第一个任务: {task.name}")

    # 查询所有记录
    enabled_tasks = db.query_all(TaskModel, deleted=False, enabled=True)
    logger.info(f"启用任务数: {len(enabled_tasks)}")
    for task in enabled_tasks[:3]:
        logger.info(f"  - {task.name}")


# ==================== 方法4: 使用 execute 执行复杂操作 ====================
def example_execute():
    """使用 execute 执行复杂操作"""
    logger.info("=== 方法4: execute 执行复杂操作 ===")

    def complex_query(db: Session):
        from sqlalchemy import func, desc

        # 统计任务数量
        total = db.query(func.count(TaskModel.id)).filter(
            TaskModel.deleted == False
        ).scalar()

        # 统计各状态任务数
        enabled = db.query(func.count(TaskModel.id)).filter(
            TaskModel.deleted == False,
            TaskModel.enabled == True
        ).scalar()

        # 获取最近执行的任务
        recent = db.query(TaskExecutionModel).order_by(
            desc(TaskExecutionModel.start_time)
        ).limit(3).all()

        return {
            "total": total,
            "enabled": enabled,
            "recent_count": len(recent)
        }

    result = db.execute(complex_query)
    logger.info(f"统计结果: 总任务={result['total']}, 启用={result['enabled']}, 最近执行={result['recent_count']}")


# ==================== 实际应用示例 ====================
def increment_task_stats(task_id: str, success: bool = True):
    """增加任务统计次数"""
    def do_increment(db: Session):
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if task:
            task.run_count = (task.run_count or 0) + 1
            if success:
                task.success_count = (task.success_count or 0) + 1
            else:
                task.failed_count = (task.failed_count or 0) + 1
            task.updated_at = datetime.now()
            logger.info(f"任务 '{task.name}' 统计已更新 (运行{task.run_count}次)")
            return True
        logger.error(f"任务不存在: {task_id}")
        return False

    return db.execute(do_increment)


def create_execution_log(task_id: str, status: str, message: str = ""):
    """创建执行日志"""
    import uuid

    execution = db.create(TaskExecutionModel,
        id=str(uuid.uuid4()),
        task_id=task_id,
        task_name=task_id,
        status=status,
        start_time=datetime.now(),
        output=message
    )

    logger.info(f"执行记录已创建: {execution.id}")
    return execution


def get_task_info(task_id: str):
    """获取任务详细信息"""
    def query(db: Session):
        task = db.query(TaskModel).filter(
            TaskModel.id == task_id,
            TaskModel.deleted == False
        ).first()

        if not task:
            logger.error(f"任务不存在: {task_id}")
            return None

        # 显示任务信息
        logger.info(f"任务名称: {task.name}")
        logger.info(f"脚本路径: {task.script_path}")
        logger.info(f"触发类型: {task.trigger_type}")
        logger.info(f"是否启用: {task.enabled}")
        logger.info(f"运行次数: {task.run_count}")
        logger.info(f"成功次数: {task.success_count}")
        logger.info(f"失败次数: {task.failed_count}")
        logger.info(f"描述: {task.description or '无'}")

        # 获取最近执行记录
        executions = db.query(TaskExecutionModel).filter(
            TaskExecutionModel.task_id == task_id
        ).order_by(desc(TaskExecutionModel.start_time)).limit(5).all()

        if executions:
            logger.info(f"最近执行记录:")
            for exe in executions:
                logger.info(f"  - {exe.status}: {exe.start_time}")

        return task

    return db.execute(query)


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("数据库操作示例开始")
    logger.info("=" * 50)

    # 获取任务ID
    task_id = os.environ.get('TASK_ID')

    # 方法1: 上下文管理器
    example_context_manager()
    logger.info("")

    # 方法2: 装饰器
    example_decorator()
    logger.info("")

    # 方法3: 辅助类
    example_helper_class()
    logger.info("")

    # 方法4: 复杂操作
    example_execute()
    logger.info("")

    # 实际应用
    if task_id:
        logger.info(f"处理当前任务: {task_id}")
        logger.info("-" * 30)

        # 获取任务信息
        get_task_info(task_id)

        # 更新统计
        increment_task_stats(task_id, success=True)

        # 创建执行记录
        create_execution_log(task_id, "success", "脚本执行成功，所有操作正常")
    else:
        logger.info("未指定任务ID (TASK_ID 环境变量)")
        logger.info("提示: 通过任务调度系统运行此脚本时，会自动设置 TASK_ID")

    logger.info("=" * 50)
    logger.info("数据库操作示例完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
