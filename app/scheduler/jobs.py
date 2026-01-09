import os
import importlib
import sys
import inspect
from typing import Dict, List, Any


def discover_tasks(refresh=False):
    """
    扫描并热加载任务脚本
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tasks_dir = os.path.join(current_dir, '..', 'tasks')
    tasks_list = []
    registry = {}
    # 遍历目录
    for file_name in os.listdir(tasks_dir):
        if file_name.endswith('.py') and file_name != '__init__.py':
            module_name = f"app.tasks.{file_name[:-3]}"
            try:
                # --- 1. 强制重载机制 ---
                if module_name in sys.modules:
                    # 使用 importlib.reload 强制重新加载模块
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)
                # --- 2. 检查属性并注册 ---
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) \
                            and not name.startswith('_') \
                            and obj.__module__.startswith('app.tasks'):
                        # 打印日志，确认加载
                        print(f"[Hot Load] Registered: {name} from {module_name}")
                        # 核心点：将新函数对象注册到本地 registry
                        registry[name] = obj
                        # 加入前端列表（文件名.函数名）
                        tasks_list.append({
                            "func_name": name,
                            "display_name": f"{file_name[:-3]}.{name}"
                        })
            except Exception as e:
                print(f"[Error] 加载脚本 {module_name} 失败: {e}")
    return registry, tasks_list


# 初始化启动
JOB_REGISTRY, AVAILABLE_TASKS_LIST = discover_tasks(refresh=True)


def get_job_func(func_name: str):
    global JOB_REGISTRY
    # 每次调用都去全局注册表找最新的引用
    func = JOB_REGISTRY.get(func_name)
    if not func:
        raise ValueError(f"Function '{func_name}' not found. Please try clicking 'Refresh Scripts'.")
    return func


def refresh_scripts():
    """
    对外暴露的刷新接口
    """
    global JOB_REGISTRY, AVAILABLE_TASKS_LIST
    print("--- 正在热加载最新脚本 ---")
    # 调用 discover_tasks，它会执行 reload 逻辑
    JOB_REGISTRY, AVAILABLE_TASKS_LIST = discover_tasks(refresh=True)
    return AVAILABLE_TASKS_LIST