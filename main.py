"""
Schedule 主入口
"""
import os
import logging
import sys

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import uvicorn
from src.app import create_app
from config import setup_logger, get_settings, load_config_file


def main():
    """主函数"""

    # 加载配置文件
    load_config_file(os.path.join(current_dir, ".env"))
    settings = get_settings()
    # 设置日志
    setup_logger(
        level=settings.LOG_LEVEL,
        log_dir=settings.LOGS_DIR
    )
    logger = logging.getLogger(__name__)

    logger.info(f"⭐⭐⭐⭐⭐⭐{settings.APP_NAME} v{settings.APP_VERSION} 开始启动⭐⭐⭐⭐⭐⭐")

    # 创建应用
    app = create_app()

    # 启动服务
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )

if __name__ == "__main__":
    main()