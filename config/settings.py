"""
配置管理模块
支持从环境变量和配置文件加载配置
"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

_settings: Optional['Settings'] = None


def load_config_file(config_path: str):
    """
    从配置文件加载配置（支持 .env 和 YAML）

    Args:
        config_path: 配置文件路径
    """
    if config_path.endswith('.env'):
        from dotenv import load_dotenv
        print(f'加载配置文件地址：{config_path}')
        load_dotenv(config_path)

    elif config_path.endswith(('.yml', '.yaml')):
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            for key, value in config_data.items():
                # 直接将配置项设置到环境变量中
                os.environ[key.upper()] = str(value)


def get_settings() -> 'Settings':
    """获取配置单例。在需要访问配置的地方调用此函数。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


@dataclass
class Settings:
    """应用配置"""

    def __init__(self):
        # 只在第一次调用 get_settings() 时初始化配置
        # 应用基础配置
        self.APP_NAME: str = os.getenv("APP_NAME", "任务调度系统")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION", "自动化任务调度系统")
        self.DEBUG: bool = bool(os.getenv("DEBUG", False))
        self.TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Shanghai")

        # API 服务配置
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = int(os.getenv("API_PORT", "8000"))
        self.API_PREFIX: str = os.getenv("API_PREFIX", "/api")

        rootPath = Path(__file__).parent.parent
        # 脚本目录配置
        self.SCRIPTS_DIR: str = str(rootPath / os.getenv("SCRIPTS_DIR", "scripts"))

        # MySQL 配置
        self.MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
        self.MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
        self.MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "test123")
        self.MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "schedule")

        # 日志配置
        self.LOGS_DIR: str = str(rootPath / os.getenv("LOGS_DIR", "logs"))
        self.LOGS_NAME: str = os.getenv("LOGS_NAME", "schedule.log")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        self.LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10")) * 1024 * 1024  # 修正这里
