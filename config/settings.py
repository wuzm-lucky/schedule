"""
配置管理模块 - 使用 Pydantic BaseSettings
支持从环境变量和配置文件加载配置
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


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
                os.environ[key.upper()] = str(value)


class Settings(BaseSettings):
    """应用配置 - 使用 Pydantic 自动验证和类型转换"""

    # ========== 应用基础配置 ==========
    app_name: str = Field(default="任务调度系统", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_description: str = Field(default="自动化任务调度系统", alias="APP_DESCRIPTION")
    debug: bool = Field(default=False, alias="DEBUG")
    timezone: str = Field(default="Asia/Shanghai", alias="TIMEZONE")

    # ========== API 服务配置 ==========
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    # ========== 脚本目录配置 ==========
    scripts_dir: str = Field(default="scripts", alias="SCRIPTS_DIR")

    @property
    def scripts_path(self) -> Path:
        """获取脚本目录绝对路径"""
        root_path = Path(__file__).parent.parent
        return root_path / self.scripts_dir

    # ========== 脚本日志目录配置 ==========
    script_logs_dir: str = Field(default="logs/script", alias="SCRIPT_LOGS_DIR")

    @property
    def script_logs_path(self) -> Path:
        """获取脚本日志目录绝对路径"""
        root_path = Path(__file__).parent.parent
        logs_path = root_path / self.script_logs_dir
        # 确保日志目录存在
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path

    # ========== MySQL 配置 ==========
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="schedule", alias="MYSQL_DATABASE")

    @property
    def database_url(self) -> str:
        """构建数据库连接 URL"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    # ========== 日志配置 ==========
    logs_dir: str = Field(default="logs", alias="LOGS_DIR")
    logs_name: str = Field(default="schedule.log", alias="LOGS_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    log_max_bytes: int = Field(default=10, alias="LOG_MAX_BYTES")

    @property
    def log_max_bytes_in_bytes(self) -> int:
        """日志文件最大字节数"""
        return self.log_max_bytes * 1024 * 1024

    @property
    def logs_path(self) -> Path:
        """获取日志目录绝对路径"""
        root_path = Path(__file__).parent.parent
        return root_path / self.logs_dir

    # ========== 验证器 ==========
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f'日志级别必须是以下之一: {valid_levels}')
        return v

    @field_validator('api_port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口号"""
        if not 1 <= v <= 65535:
            raise ValueError('端口号必须在 1-65535 之间')
        return v

    class Config:
        """Pydantic 配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
        populate_by_name = True  # 支持别名


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()