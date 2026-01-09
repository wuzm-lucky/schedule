import os
from dotenv import load_dotenv
from pathlib import Path

# 1. 获取当前 config.py 文件所在的绝对路径
# 例如：E:\WorkSpace\PyCharm\schedule\config.py
CURRENT_FILE_PATH = Path(__file__).absolute()

# 2. 获取 config.py 的父目录，这就是项目根目录
# 例如：E:\WorkSpace\PyCharm\schedule
PROJECT_ROOT = CURRENT_FILE_PATH.parent

# 3. 拼接 .env 文件的绝对路径
ENV_FILE = PROJECT_ROOT / ".env"

# 4. 显式加载该路径
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"[Config] 已加载配置文件: {ENV_FILE}")
else:
    print(f"[Config] 警告：未在根目录找到 .env 文件，路径为 {ENV_FILE}")

class Settings:
    # 2. 使用 os.getenv 获取环境变量，并设置默认值（防止没找到报错）
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "task_scheduler")
    # APP 配置
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))

    # 调度器配置
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai")

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()