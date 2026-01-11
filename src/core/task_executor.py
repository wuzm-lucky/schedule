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
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from config import get_settings
from src.models.task import Task

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CommandBuilder:
    """命令构建器"""
    extensions: List[str]
    command: List[str]
    check_executable: Optional[Callable[[str], bool]] = None

    def build(self, script_path: str, arguments: List[str]) -> List[str]:
        """构建命令"""
        if self.check_executable:
            if not self.check_executable(self.command[0]):
                raise RuntimeError(f"Executable not found: {self.command[0]}")
        return self.command + [script_path] + arguments


class TaskExecutor:
    """任务执行器 - 使用 subprocess 进程隔离执行脚本"""

    # 支持的脚本类型命令构建器
    COMMAND_BUILDERS: List[CommandBuilder] = [
        CommandBuilder(['.py'], [sys.executable]),
        CommandBuilder(['.sh'], ['/bin/bash']),
        CommandBuilder(['.bash'], ['/bin/bash']),
        CommandBuilder(['.bat', '.cmd'], ['cmd.exe', '/c']),
        CommandBuilder(['.js'], ['node']),
        CommandBuilder(['.ts'], ['npx', 'ts-node']),
        CommandBuilder(['.ps1'], ['pwsh', '-File'], lambda x: self._check_pwsh(x)),
        CommandBuilder(['.rb'], ['ruby']),
        CommandBuilder(['.php'], ['php']),
        CommandBuilder(['.pl'], ['perl']),
    ]

    @staticmethod
    def _check_pwsh(executable: str) -> bool:
        """检查 PowerShell 是否可用"""
        try:
            result = subprocess.run(
                [executable, '-Version'],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False

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
            cmd = self._build_command(task, script_path)
            logger.info(f"Command: {' '.join(cmd)}")

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

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": self._decode_output(result.stdout),
                "stderr": self._decode_output(result.stderr),
                "duration": duration
            }

        except subprocess.TimeoutExpired as e:
            logger.error(f"Task timeout: {task.id}")
            return {
                "success": False,
                "error": f"Task execution timeout after {task.timeout} seconds",
                "exit_code": -1,
                "stdout": self._decode_output(getattr(e, 'stdout', b'')),
                "stderr": self._decode_output(getattr(e, 'stderr', b''))
            }

        except FileNotFoundError as e:
            error_detail = f"Executable not found: {e.filename}"
            logger.error(f"Task execution error: {task.id} - {error_detail}")
            return {
                "success": False,
                "error": error_detail,
                "exit_code": -1
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
                      callback: Optional[Callable] = None) -> str:
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

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=task.working_directory or os.path.dirname(script_path),
            env=self._build_env(task.environment),
            bufsize=1
        )

        self._running_processes[execution_id] = process

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
        """
        解析脚本路径

        优先级:
        1. 绝对路径
        2. scripts 目录相对路径
        3. 当前工作目录相对路径
        """
        # 绝对路径
        if os.path.isabs(script_path):
            return script_path if os.path.exists(script_path) else None

        # scripts 目录
        scripts_path = settings.scripts_path / script_path
        if scripts_path.exists():
            return str(scripts_path)

        # 当前工作目录
        cwd_path = Path.cwd() / script_path
        if cwd_path.exists():
            return str(cwd_path)

        return None

    def _build_command(self, task: Task, script_path: str) -> List[str]:
        """构建执行命令"""
        ext = os.path.splitext(script_path)[1].lower()

        # 查找匹配的命令构建器
        for builder in self.COMMAND_BUILDERS:
            if ext in builder.extensions:
                return builder.build(script_path, task.arguments)

        # 默认直接执行
        logger.warning(f"Unknown script type: {ext}, executing directly")
        return [script_path] + task.arguments

    def _build_env(self, task_env: Optional[Dict[str, str]]) -> Dict[str, str]:
        """构建环境变量"""
        env = os.environ.copy()
        if task_env:
            env.update(task_env)
        return env

    def _decode_output(self, output: bytes) -> str:
        """
        解码输出，支持多种编码

        尝试顺序: utf-8 -> gbk -> 系统默认 -> 替换模式
        """
        if not output:
            return ""

        encodings = ['utf-8', 'gbk', sys.getdefaultencoding()]
        for encoding in encodings:
            try:
                return output.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        # 最后使用替换模式
        return output.decode('utf-8', errors='replace')
