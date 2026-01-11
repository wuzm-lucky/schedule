"""
任务脚本日志工具

提供便捷的日志配置方法，统一管理脚本日志输出
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def setup_script_logger(
    level: str = "INFO",
    format_string: str = "%(asctime)s - %(levelname)s - %(message)s",
    console: bool = False
) -> logging.Logger:
    """
    配置任务脚本日志

    自动从环境变量获取日志文件路径，并配置日志输出。
    日志文件使用 UTF-8 编码，确保中文正确显示。

    Args:
        level: 日志级别，默认 "INFO"
        format_string: 日志格式字符串
        console: 是否同时输出到控制台，默认 False

    Returns:
        logging.Logger: 配置好的 logger 实例

    使用示例:
        from src.utils.logger import setup_script_logger

        logger = setup_script_logger()
        logger.info("这是一条日志")
        logger.error("这是错误信息")
    """
    # 获取日志文件路径
    log_file = os.environ.get('TASK_SCRIPT_LOG')

    # 如果没有日志文件路径，尝试使用默认的 script_logs 目录
    if not log_file:
        script_name = os.path.basename(sys.argv[0]).replace('.py', '')
        log_dir = project_root / 'script_logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / f"{script_name}.log")

    # 创建 logger
    logger = logging.getLogger(f"script_{id(object())}")  # 使用唯一名称避免冲突
    logger.setLevel(getattr(logging, level.upper()))

    # 清除已有的 handlers
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(format_string)

    # 文件处理器 - 使用 UTF-8 编码
    try:
        file_handler = logging.FileHandler(
            log_file,
            mode='a',
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, level.upper()))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"无法创建日志文件: {e}", file=sys.stderr)

    # 控制台处理器（可选）
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, level.upper()))
        logger.addHandler(console_handler)

    return logger


def get_script_logger(name: str = None) -> logging.Logger:
    """
    获取或创建脚本日志器（便捷方法）

    如果已经配置过则返回现有的，否则自动配置并返回新的。

    Args:
        name: logger 名称，默认使用脚本文件名

    Returns:
        logging.Logger: logger 实例

    使用示例:
        from src.utils.logger import get_script_logger

        logger = get_script_logger()
        logger.info("这是一条日志")
    """
    if name:
        logger = logging.getLogger(name)
    else:
        # 使用调用脚本的文件名作为 logger 名称
        import traceback
        stack = traceback.extract_stack()
        # 找到调用本模块的脚本
        for frame in stack:
            if 'scripts' in frame.filename and frame.name != '<module>':
                script_name = Path(frame.filename).stem
                name = f"script_{script_name}"
                break
        else:
            name = "script_default"

    logger = logging.getLogger(name)

    # 如果还没有配置过，自动配置
    if not logger.handlers:
        return setup_script_logger(level="INFO", console=False)

    return logger


# 为了兼容性，也创建一个默认 logger
default_logger = get_script_logger()

# 便捷的日志函数
def log_info(message: str):
    """记录 INFO 级别日志"""
    default_logger.info(message)

def log_warning(message: str):
    """记录 WARNING 级别日志"""
    default_logger.warning(message)

def log_error(message: str):
    """记录 ERROR 级别日志"""
    default_logger.error(message)

def log_debug(message: str):
    """记录 DEBUG 级别日志"""
    default_logger.debug(message)
