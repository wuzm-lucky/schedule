import logging
import os

# 获取日志文件路径
log_file = os.environ.get('TASK_SCRIPT_LOG')
if log_file:
    # 配置日志输出到文件
    # 重要：指定 encoding='utf-8' 确保中文正确写入
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a',  # 追加模式
        encoding='utf-8'  # 指定使用 UTF-8 编码
    )

    # 记录重要信息
    logging.info("这是一条重要日志")
    logging.error("发生错误")