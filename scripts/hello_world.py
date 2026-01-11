#!/usr/bin/env python3
"""
示例任务：Hello World
最简单的测试任务
"""

import sys
import logging
from datetime import datetime

def main():
    """主函数"""
    logger = logging.getLogger(__name__)
    logger.info(f"※※※※※这是{__name__}脚本※※※※※")
    print(f"[{datetime.now()}] Hello, Task Worker!")
    print("This is a test task.")
    print("Arguments received:", sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
