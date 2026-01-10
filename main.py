"""
Schedule 主入口
"""
import os
import logging
import sys
import uvicorn

from config import load_config_file
# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
# 加载配置文件（在获取 settings 之前）
load_config_file(os.path.join(current_dir, ".env"))

from src.app import create_app
from config import setup_logger, get_settings


def main():
    """主函数"""
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