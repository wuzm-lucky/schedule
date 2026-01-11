"""
日志工具使用示例
展示如何使用封装后的日志工具
"""

import sys
import os

# 添加项目根目录到路径（确保能导入项目模块）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入日志工具
from src.utils.logger import setup_script_logger, get_script_logger, log_info, log_error

# ==================== 方式1: 使用 setup_script_logger ====================
def example_setup():
    """方式1: 使用 setup_script_logger 配置日志"""
    logger = setup_script_logger()
    logger.info("使用 setup_script_logger 配置的日志")
    logger.error("这是一条错误信息")


# ==================== 方式2: 使用 get_script_logger ====================
def example_get_logger():
    """方式2: 使用 get_script_logger 获取日志器"""
    logger = get_script_logger()
    logger.info("使用 get_script_logger 获取的日志")
    logger.warning("这是一条警告信息")


# ==================== 方式3: 使用便捷函数 ====================
def example_convenience():
    """方式3: 使用便捷日志函数"""
    log_info("使用便捷函数记录的日志")
    log_error("使用便捷函数记录的错误")


# ==================== 方式4: 带自定义配置 ====================
def example_custom():
    """方式4: 自定义配置"""
    logger = setup_script_logger(
        level="DEBUG",
        format_string="%(asctime)s [%(levelname)s] %(message)s",
        console=True  # 同时输出到控制台
    )
    logger.debug("这是调试信息")
    logger.info("这是普通信息")


# ==================== 实际应用示例 ====================
def process_task():
    """实际应用：处理任务"""
    # 获取环境变量
    task_id = os.environ.get('TASK_ID', 'unknown')

    # 获取日志器
    logger = get_script_logger()

    logger.info(f"=== 任务开始处理: {task_id} ===")

    # 模拟处理过程
    logger.info("步骤1: 验证输入参数")
    logger.info("步骤2: 连接数据库")
    logger.info("步骤3: 执行业务逻辑")
    logger.info("步骤4: 保存结果")

    logger.info(f"=== 任务处理完成: {task_id} ===")


def main():
    """主函数"""
    # 方式1
    example_setup()

    # 方式2
    example_get_logger()

    # 方式3
    example_convenience()

    # 方式4
    # example_custom()  # 取消注释可查看控制台输出

    # 实际应用
    process_task()


if __name__ == "__main__":
    main()
