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

    def _get_script_log_file(self, script_path: str) -> Path:
        """
        获取脚本对应的日志文件路径

        日志文件名为脚本名（去掉扩展名）+ .log
        例如: test.py -> test.log

        Args:
            script_path: 脚本文件路径

        Returns:
            日志文件路径
        """
        script_name = Path(script_path).stem  # 获取不带扩展名的文件名
        log_file = settings.script_logs_path / f"{script_name}.log"
        return log_file

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

        # 获取脚本日志文件
        log_file = self._get_script_log_file(script_path)
        log_handle = None

        try:
            cmd = self._build_command(task, script_path)
            logger.info(f"Command: {' '.join(cmd)}")

            # 构建环境变量，添加日志文件路径
            env = self._build_env(task.environment)
            env["TASK_SCRIPT_LOG"] = str(log_file)
            env["TASK_EXECUTION_ID"] = execution_id
            env["TASK_ID"] = task.id

            # 打开日志文件用于追加输出（二进制模式，便于编码转换）
            log_handle = open(log_file, 'ab')

            # 写入执行开始标记（UTF-8编码）
            header = f"\n{'='*80}\n"
            header += f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 执行开始\n"
            header += f"任务ID: {task.id}\n"
            header += f"任务名称: {task.name}\n"
            header += f"执行ID: {execution_id}\n"
            header += f"脚本: {script_path}\n"
            header += f"参数: {' '.join(task.arguments) if task.arguments else '无'}\n"
            header += f"{'='*80}\n"
            log_handle.write(header.encode('utf-8'))
            log_handle.flush()

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=task.timeout,
                cwd=task.working_directory or os.path.dirname(script_path),
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            duration = (datetime.now() - start_time).total_seconds()

            # 写入执行结果到日志文件
            end_time = datetime.now()
            footer = f"\n{'-'*80}\n"
            footer += f"执行结果: {'成功' if result.returncode == 0 else '失败'}\n"
            footer += f"退出码: {result.returncode}\n"
            footer += f"耗时: {duration:.2f}秒\n"
            footer += f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            log_handle.write(footer.encode('utf-8'))

            # 写入标准输出（转换为UTF-8字节）
            if result.stdout:
                log_handle.write("\n[标准输出]\n".encode('utf-8'))
                log_handle.write(self._convert_to_utf8_bytes(result.stdout))
                if result.stdout and result.stdout[-1:] != b'\n':
                    log_handle.write('\n'.encode('utf-8'))

            # 写入标准错误（转换为UTF-8字节）
            if result.stderr:
                log_handle.write("\n[标准错误]\n".encode('utf-8'))
                log_handle.write(self._convert_to_utf8_bytes(result.stderr))
                if result.stderr and result.stderr[-1:] != b'\n':
                    log_handle.write('\n'.encode('utf-8'))

            log_handle.write(f"{'='*80}\n".encode('utf-8'))
            log_handle.close()
            log_handle = None

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": self._decode_output(result.stdout),  # API返回原始解码
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

        finally:
            # 确保日志文件被关闭
            if log_handle and not log_handle.closed:
                try:
                    log_handle.close()
                except Exception:
                    pass

    def _log_error_to_file(self, log_handle, error_message: str, exception: Exception, start_time: datetime):
        """记录错误到日志文件"""
        if not log_handle or log_handle.closed:
            return

        try:
            duration = (datetime.now() - start_time).total_seconds()
            error_footer = f"\n{'-'*80}\n"
            error_footer += f"执行结果: 失败\n"
            error_footer += f"错误: {error_message}\n"
            error_footer += f"耗时: {duration:.2f}秒\n"
            error_footer += f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            log_handle.write(error_footer.encode('utf-8'))

            # 如果有输出，也记录（转换为UTF-8字节）
            if hasattr(exception, 'stdout') and exception.stdout:
                stdout_bytes = exception.stdout if isinstance(exception.stdout, bytes) else str(exception.stdout).encode('utf-8')
                log_handle.write("\n[标准输出]\n".encode('utf-8'))
                log_handle.write(self._convert_to_utf8_bytes(stdout_bytes))
                log_handle.write('\n'.encode('utf-8'))

            if hasattr(exception, 'stderr') and exception.stderr:
                stderr_bytes = exception.stderr if isinstance(exception.stderr, bytes) else str(exception.stderr).encode('utf-8')
                log_handle.write("\n[标准错误]\n".encode('utf-8'))
                log_handle.write(self._convert_to_utf8_bytes(stderr_bytes))
                log_handle.write('\n'.encode('utf-8'))

            log_handle.write(f"{'='*80}\n".encode('utf-8'))
            log_handle.flush()
        except Exception:
            pass

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

    def _convert_to_utf8_bytes(self, output: bytes) -> bytes:
        """
        将原始字节转换为UTF-8字节

        假设脚本已经配置为UTF-8输出，但仍做兼容性检测
        """
        if not output:
            return b""

        # 尝试使用 chardet 检测编码
        try:
            import chardet
            detection = chardet.detect(output)
            detected_encoding = detection.get('encoding', 'utf-8')
            confidence = detection.get('confidence', 0)

            # 如果检测到的不是UTF-8，需要转换
            if detected_encoding.lower() not in ['utf-8', 'ascii']:
                try:
                    text = output.decode(detected_encoding)
                    return text.encode('utf-8')
                except:
                    pass
        except ImportError:
            pass

        # 尝试UTF-8解码（直接返回）
        try:
            output.decode('utf-8')
            return output
        except UnicodeDecodeError:
            pass

        # 回退到GBK（Windows中文）
        try:
            text = output.decode('gbk')
            return text.encode('utf-8')
        except:
            pass

        # 最后尝试系统默认编码
        try:
            text = output.decode(sys.getdefaultencoding())
            return text.encode('utf-8')
        except:
            # 强制UTF-8替换模式
            text = output.decode('utf-8', errors='replace')
            return text.encode('utf-8')
