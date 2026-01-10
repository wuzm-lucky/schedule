"""
任务执行器模块
使用 subprocess 实现进程级隔离，执行各类自动化脚本
"""

import logging
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.models.task import Task

logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器 - 使用 subprocess 进程隔离执行脚本"""

    def __init__(self):
        self._running_processes: Dict[str, subprocess.Popen] = {}

    def execute(self, task: Task, execution_id: str) -> Dict[str, Any]:
        """
        执行任务

        Args:
            task: 任务对象
            execution_id: 执行ID

        Returns:
            执行结果字典
        """
        start_time = datetime.now()
        script_path = self._resolve_script_path(task.script_path)

        if not script_path or not os.path.exists(script_path):
            return {
                "success": False,
                "error": f"Script not found: {task.script_path}",
                "exit_code": -1
            }

        logger.info(f"Executing task: {task.id}, script: {script_path}, execution_id: {execution_id}")

        try:
            # 构建执行命令
            cmd = self._build_command(task, script_path)
            logger.info(f"Command: {' '.join(cmd)}")

            # 执行脚本 - 使用更稳定的参数
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=task.timeout,
                cwd=task.working_directory or os.path.dirname(script_path),
                env=self._build_env(task.environment),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            duration = (datetime.now() - start_time).total_seconds()

            # 手动解码输出，处理编码错误
            try:
                stdout = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                stdout = result.stdout.decode('gbk', errors='replace')

            try:
                stderr = result.stderr.decode('utf-8')
            except UnicodeDecodeError:
                stderr = result.stderr.decode('gbk', errors='replace')

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration": duration
            }

        except subprocess.TimeoutExpired as e:
            logger.error(f"Task timeout: {task.id}")
            # 尝试获取已产生的输出
            stdout = stderr = ""
            if e.stdout:
                try:
                    stdout = e.stdout.decode('utf-8', errors='replace')
                except:
                    pass
            if e.stderr:
                try:
                    stderr = e.stderr.decode('utf-8', errors='replace')
                except:
                    pass
            return {
                "success": False,
                "error": f"Task execution timeout after {task.timeout} seconds",
                "exit_code": -1,
                "stdout": stdout,
                "stderr": stderr
            }

        except Exception as e:
            import traceback
            error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Task execution error: {task.id} - {error_detail}")
            return {
                "success": False,
                "error": error_detail,
                "exit_code": -1
            }

    def execute_async(self, task: Task, execution_id: str,
                      callback: Optional[callable] = None) -> str:
        """
        异步执行任务（带实时日志流）

        Args:
            task: 任务对象
            execution_id: 执行ID
            callback: 执行完成回调函数

        Returns:
            进程ID
        """
        script_path = self._resolve_script_path(task.script_path)
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {task.script_path}")

        cmd = self._build_command(task, script_path)

        # 创建日志队列
        log_queue = queue.Queue()

        # 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=task.working_directory or os.path.dirname(script_path),
            env=self._build_env(task.environment),
            bufsize=1  # 行缓冲
        )

        self._running_processes[execution_id] = process

        # 等待进程完成的线程
        def wait_for_completion():
            process.wait()

            self._running_processes.pop(execution_id, None)

            result = {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "execution_id": execution_id
            }

            if callback:
                callback(result)

        threading.Thread(target=wait_for_completion, daemon=True).start()

        logger.info(f"Async task started: {task.id}, pid: {process.pid}")
        return str(process.pid)

    def cancel(self, execution_id: str) -> bool:
        """取消正在执行的任务"""
        process = self._running_processes.get(execution_id)
        if process:
            try:
                process.terminate()
                # 等待最多5秒
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return True
            except Exception as e:
                logger.error(f"Failed to cancel task {execution_id}: {e}")
                return False
        return False

    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        return list(self._running_processes.keys())

    def _resolve_script_path(self, script_path: str) -> Optional[str]:
        """解析脚本路径"""
        # 支持绝对路径和相对路径
        if os.path.isabs(script_path):
            return script_path if os.path.exists(script_path) else None

        # 尝试在 scripts 目录查找
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        absolute_path = scripts_dir / script_path

        if absolute_path.exists():
            return str(absolute_path)

        # 尝试相对于工作目录
        cwd_path = Path.cwd() / script_path
        if cwd_path.exists():
            return str(cwd_path)

        return None

    def _build_command(self, task: Task, script_path: str) -> List[str]:
        """构建执行命令"""
        ext = os.path.splitext(script_path)[1].lower()

        if ext == '.py':
            return [sys.executable, script_path] + task.arguments

        elif ext == '.sh':
            return ['/bin/bash', script_path] + task.arguments

        elif ext == '.bat' or ext == '.cmd':
            return ['cmd.exe', '/c', script_path] + task.arguments

        elif ext == '.js':
            return ['node', script_path] + task.arguments

        else:
            # 尝试直接执行（需要可执行权限）
            return [script_path] + task.arguments

    def _build_env(self, task_env: Optional[Dict[str, str]]) -> Dict[str, str]:
        """构建环境变量"""
        env = os.environ.copy()
        if task_env:
            env.update(task_env)
        return env
