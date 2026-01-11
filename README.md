# Schedule - 任务调度系统

一个基于 FastAPI 和 APScheduler 的分布式任务调度系统，支持多种触发器类型、脚本语言和任务管理功能。

## 特性

- **多种触发器类型**：支持 cron 表达式、固定间隔、一次性定时任务
- **多语言脚本支持**：Python、Shell、Batch、JavaScript、TypeScript、PowerShell、Ruby、PHP、Perl
- **Web 管理界面**：直观的任务管理和执行监控
- **任务执行日志**：独立的脚本日志文件，支持 UTF-8 编码
- **数据库持久化**：使用 MySQL 存储任务配置和执行记录
- **RESTful API**：完整的任务管理 API 接口
- **跨平台支持**：自动检测可执行文件，支持 Windows/Linux/macOS

## 项目结构

```
schedule/
├── config/                  # 配置模块
│   ├── __init__.py         # 配置导出
│   ├── settings.py         # Pydantic 配置定义
│   └── database.py         # 数据库连接和辅助类
├── src/
│   ├── api/                # API 路由层
│   │   ├── tasks.py        # 任务管理接口
│   │   └── health.py       # 健康检查接口
│   ├── core/               # 核心业务逻辑
│   │   ├── scheduler.py    # APScheduler 封装
│   │   └── task_executor.py # 脚本执行引擎
│   ├── models/             # 数据模型
│   │   ├── task.py         # 领域模型
│   │   ├── database.py     # ORM 模型
│   │   └── response.py     # API 响应模型
│   ├── repository/         # 数据访问层
│   │   ├── base.py         # 通用仓储基类
│   │   └── task_repository.py # 任务仓储
│   ├── services/           # 业务服务层
│   │   ├── task_service.py    # 任务服务
│   │   └── execution_service.py # 执行记录服务
│   ├── middleware/         # 中间件
│   │   └── exception_handler.py # 异常处理
│   ├── utils/              # 工具模块
│   │   └── logger.py       # 日志工具
│   ├── constants.py        # 全局常量定义
│   ├── exceptions.py       # 自定义异常
│   └── app.py              # FastAPI 应用工厂
├── scripts/                # 可执行脚本目录
│   ├── db_helper_example.py  # 数据库操作示例
│   └── logger_example.py    # 日志使用示例
├── templates/              # HTML 模板
│   └── dashboard.html      # 管理后台页面
├── static/                 # 静态资源
│   ├── css/                # 样式文件
│   └── js/                 # JavaScript 文件
├── logs/                   # 日志目录
│   └── script/             # 脚本执行日志目录
├── .env                    # 环境变量配置
├── main.py                 # 应用入口
└── requirements.txt        # Python 依赖
```

## 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+
- pip

### 安装

1. 克隆项目：
```bash
git clone <repository-url>
cd schedule
```

2. 创建虚拟环境并安装依赖：
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境变量（复制 `.env.example` 到 `.env`）：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接等参数：
```env
# 应用配置
APP_NAME=任务调度系统
DEBUG=False
TIMEZONE=Asia/Shanghai

# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/schedule_db?charset=utf8mb4

# 脚本目录
SCRIPTS_DIR=scripts
SCRIPT_LOGS_DIR=logs/script
```

4. 初始化数据库：
```bash
python -c "from config.database import init_db; init_db()"
```

5. 启动应用：
```bash
python main.py
```

6. 访问管理界面：
```
http://localhost:8000/
```

## API 文档

启动应用后，访问以下地址查看完整 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tasks` | 获取任务列表 |
| POST | `/tasks` | 创建新任务 |
| GET | `/tasks/{task_id}` | 获取任务详情 |
| PUT | `/tasks/{task_id}` | 更新任务 |
| DELETE | `/tasks/{task_id}` | 删除任务 |
| POST | `/tasks/{task_id}/pause` | 暂停任务 |
| POST | `/tasks/{task_id}/resume` | 恢复任务 |
| POST | `/tasks/execute` | 立即执行任务 |
| GET | `/tasks/{task_id}/executions` | 获取执行记录 |
| GET | `/scripts` | 获取脚本列表 |

## 任务配置

### Cron 表达式

支持 5 字段（标准 Unix）和 6 字段（包含秒）格式：

```
# 每分钟执行
* * * * *

# 每天 12:00 执行
0 12 * * *

# 每 5 秒执行（6 字段格式）
*/5 * * * * *
```

### 固定间隔

以秒为单位的固定时间间隔：

```json
{
  "trigger_type": "interval",
  "interval_seconds": 60
}
```

### 一次性任务

指定具体的执行时间：

```json
{
  "trigger_type": "date",
  "scheduled_time": "2026-01-12 12:00:00"
}
```

## 脚本开发

### 脚本日志

每个脚本都有独立的日志文件（与脚本同名），可以通过环境变量 `TASK_SCRIPT_LOG` 获取日志文件路径：

```python
# scripts/my_task.py
import os
import logging

log_file = os.environ.get('TASK_SCRIPT_LOG')
if log_file:
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a',
        encoding='utf-8'  # 重要：确保中文正常显示
    )

logging.info("任务开始执行")
# ... 业务逻辑
logging.info("任务执行完成")
```

### 数据库操作

使用封装好的数据库工具简化操作：

```python
# scripts/db_example.py
from src.utils.logger import get_script_logger
from config.database import get_db_session, with_db, db
from src.models.database import TaskModel

# 获取日志器
logger = get_script_logger()

# 方式1: 上下文管理器
with get_db_session() as db:
    tasks = db.query(TaskModel).filter(TaskModel.enabled == True).all()
    logger.info(f"找到 {len(tasks)} 个任务")

# 方式2: 装饰器
@with_db
def get_task_name(db, task_id: str):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    return task.name if task else None

# 方式3: DatabaseHelper
task = db.query_one(TaskModel, id=task_id)
tasks = db.query_all(TaskModel, enabled=True)
```

### 环境变量

脚本执行时会自动设置以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `TASK_ID` | 任务ID | `eaede221-e537-495b-893e-b4b47c154f27` |
| `TASK_EXECUTION_ID` | 执行ID | `eaede221_20260111232712365` |
| `TASK_SCRIPT_LOG` | 日志文件路径 | `/path/to/logs/script/my_task.log` |

## 代码优化

本项目经过系统性优化，主要改进包括：

### 1. 全局常量管理

创建了 `src/constants.py` 统一管理系统常量：

```python
from src.constants import SchedulerConfig, ValidationConfig

# 使用配置常量
max_instances = SchedulerConfig.MAX_INSTANCES  # 1
misfire_grace_time = SchedulerConfig.MISFIRE_GRACE_TIME  # 300
```

### 2. 跨平台兼容性

使用 `shutil.which` 自动检测可执行文件：

```python
# 自动查找 node、nodejs 等可执行文件
CommandBuilder(['.js'], ['node', 'nodejs'])
```

支持的脚本类型：
- `.py` - Python
- `.sh/.bash` - Shell/Bash
- `.bat/.cmd` - Windows Batch
- `.js` - JavaScript (Node.js)
- `.ts` - TypeScript (ts-node)
- `.ps1` - PowerShell
- `.rb` - Ruby
- `.php` - PHP
- `.pl` - Perl

### 3. 结构化错误处理

增强的异常系统，支持详细信息：

```python
from src.exceptions import (
    TaskNotFoundException,
    TaskValidationException,
    ScriptNotFoundException,
    CronExpressionException
)

# 带详细信息的异常
raise TaskNotFoundException(task_id="xxx")
# {"code": "task_not_found", "message": "任务不存在: xxx", "details": {"task_id": "xxx"}}
```

### 4. 输入验证

使用 Pydantic 验证器自动验证请求参数：

```python
class TaskAddRequest(BaseModel):
    task_name: str
    timeout: int = 300
    cron_expression: Optional[str] = None

    @field_validator('task_name')
    @classmethod
    def validate_task_name(cls, v: str) -> str:
        if not (1 <= len(v) <= 100):
            raise ValueError('任务名称长度必须在1-100之间')
        return v.strip()
```

### 5. 方法拆分

将复杂方法拆分为更小的单一职责方法：

```python
# 优化前：80 行的 add_task 方法

# 优化后：拆分为多个小方法
def add_task(self, task: Task, ...) -> bool:
    task = self._ensure_domain_model(task)
    if save_to_db:
        self._save_task_to_db(task)
    if task.enabled or force_add:
        self._schedule_task(task)
    return True
```

### 6. 数据库辅助类

`DatabaseHelper` 提供便捷的数据库操作：

| 方法 | 说明 |
|------|------|
| `query_one(model, **filters)` | 查询单条记录 |
| `query_all(model, **filters)` | 查询所有记录 |
| `create(model, **kwargs)` | 创建新记录 |
| `update(model, filters, **kwargs)` | 更新记录 |
| `delete(model, **filters)` | 删除记录 |
| `execute(func)` | 执行自定义操作 |

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 应用名称 | 任务调度系统 |
| `DEBUG` | 调试模式 | False |
| `TIMEZONE` | 时区 | Asia/Shanghai |
| `DATABASE_URL` | 数据库连接 | - |
| `SCRIPTS_DIR` | 脚本目录 | scripts |
| `SCRIPT_LOGS_DIR` | 脚本日志目录 | logs/script |

### 调度器配置

| 常量 | 说明 | 默认值 |
|------|------|--------|
| `MAX_INSTANCES` | 最大并发实例 | 1 |
| `MISFIRE_GRACE_TIME` | 错过执行宽限时间 | 300秒 |
| `DEFAULT_TIMEOUT` | 默认超时时间 | 300秒 |

## 常见问题

### 1. 中文乱码问题

确保在脚本配置日志时添加 `encoding='utf-8'`：

```python
logging.basicConfig(
    filename=log_file,
    encoding='utf-8',  # 必须添加
    ...
)
```

### 2. 脚本找不到可执行文件

系统会自动检测常见的可执行文件路径。如果找不到，请确保：

- 可执行文件在系统 PATH 环境变量中
- 或者使用绝对路径指定可执行文件

### 3. 任务不执行

检查以下项：

1. 任务的 `enabled` 状态是否为 `True`
2. cron 表达式格式是否正确
3. 查看应用日志 `logs/schedule.log`

## 开发指南

### 添加新的触发器类型

1. 在 `src/models/task.py` 中添加 `TriggerType` 枚举
2. 在 `scheduler.py` 的 `_create_trigger` 方法中实现触发器逻辑
3. 更新 API 验证规则

### 添加新的脚本类型

1. 在 `src/constants.py` 的 `ScriptConfig.EXECUTABLE_MAP` 中添加映射
2. 在 `task_executor.py` 的 `COMMAND_BUILDERS` 中添加构建器

## 许可证

MIT License
