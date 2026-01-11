"""
数据库使用示例脚本
展示如何在任务脚本中访问和操作数据库
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到路径（确保能导入项目模块）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据库相关模块
from config.database import SessionLocal
from src.models.database import TaskModel, TaskExecutionModel
from sqlalchemy import func, desc

# 配置日志输出到文件
log_file = os.environ.get('TASK_SCRIPT_LOG')
if log_file:
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a',
        encoding='utf-8'
    )


def query_tasks():
    """查询任务列表"""
    db = SessionLocal()
    try:
        # 查询所有启用的任务
        tasks = db.query(TaskModel).filter(
            TaskModel.deleted == False
        ).order_by(desc(TaskModel.created_at)).all()

        logging.info(f"找到 {len(tasks)} 个任务")
        for task in tasks:
            logging.info(f"任务: {task.name} - 启用: {task.enabled}")

        return tasks
    finally:
        db.close()


def query_single_task(task_id: str):
    """查询单个任务"""
    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(
            TaskModel.id == task_id,
            TaskModel.deleted == False
        ).first()

        if task:
            logging.info(f"任务详情: {task.name}")
            logging.info(f"脚本路径: {task.script_path}")
            logging.info(f"触发类型: {task.trigger_type}")
            logging.info(f"运行次数: {task.run_count}")
        else:
            logging.warning(f"任务不存在: {task_id}")

        return task
    finally:
        db.close()


def update_task_stats(task_id: str, success: bool = True):
    """更新任务统计信息"""
    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if task:
            task.run_count = (task.run_count or 0) + 1
            if success:
                task.success_count = (task.success_count or 0) + 1
            else:
                task.failed_count = (task.failed_count or 0) + 1
            task.updated_at = datetime.now()

            db.commit()
            logging.info(f"任务统计已更新: {task_id}")
        else:
            logging.error(f"任务不存在: {task_id}")
    except Exception as e:
        db.rollback()
        logging.error(f"更新失败: {e}")
    finally:
        db.close()


def create_execution_record(task_id: str, status: str, output: str = None, error: str = None):
    """创建执行记录"""
    db = SessionLocal()
    try:
        import uuid
        execution_id = str(uuid.uuid4())

        execution = TaskExecutionModel(
            id=execution_id,
            task_id=task_id,
            task_name=task_id,  # 可以查询获取真实任务名
            status=status,
            start_time=datetime.now(),
            output=output,
            error=error
        )

        db.add(execution)
        db.commit()
        logging.info(f"执行记录已创建: {execution_id}")
    except Exception as e:
        db.rollback()
        logging.error(f"创建执行记录失败: {e}")
    finally:
        db.close()


def get_task_statistics():
    """获取任务统计信息"""
    db = SessionLocal()
    try:
        # 统计总任务数
        total_tasks = db.query(func.count(TaskModel.id)).filter(
            TaskModel.deleted == False
        ).scalar()

        # 统计启用任务数
        enabled_tasks = db.query(func.count(TaskModel.id)).filter(
            TaskModel.deleted == False,
            TaskModel.enabled == True
        ).scalar()

        # 统计总运行次数
        total_runs = db.query(func.sum(TaskModel.run_count)).filter(
            TaskModel.deleted == False
        ).scalar() or 0

        # 统计总成功次数
        total_success = db.query(func.sum(TaskModel.success_count)).filter(
            TaskModel.deleted == False
        ).scalar() or 0

        logging.info("=== 任务统计 ===")
        logging.info(f"总任务数: {total_tasks}")
        logging.info(f"启用任务数: {enabled_tasks}")
        logging.info(f"总运行次数: {total_runs}")
        logging.info(f"总成功次数: {total_success}")

        # 获取最近5条执行记录
        recent_executions = db.query(TaskExecutionModel).order_by(
            desc(TaskExecutionModel.start_time)
        ).limit(5).all()

        logging.info("\n最近执行记录:")
        for exec in recent_executions:
            logging.info(f"  - {exec.task_id}: {exec.status} ({exec.start_time})")

    finally:
        db.close()


def main():
    """主函数"""
    logging.info("=== 数据库示例脚本开始执行 ===")

    # 获取任务ID环境变量（如果有的话）
    task_id = os.environ.get('TASK_ID')

    if task_id:
        # 如果有任务ID，查询单个任务
        logging.info(f"当前任务ID: {task_id}")
        query_single_task(task_id)

        # 模拟更新统计
        update_task_stats(task_id, success=True)

        # 创建执行记录
        create_execution_record(task_id, "success", "脚本执行成功")
    else:
        # 没有任务ID，显示所有任务和统计
        logging.info("没有指定任务ID，显示所有任务")
        query_tasks()
        get_task_statistics()

    logging.info("=== 数据库示例脚本执行完成 ===")


if __name__ == "__main__":
    main()
