/**
 * 任务弹窗组件
 */

import { api } from './api.js';

export class TaskModal {
    constructor() {
        this.modal = null;
        this.isEditMode = false;
        this.onSave = null;
    }

    async init() {
        await this.loadScripts();
        this.modal = new bootstrap.Modal(document.getElementById('addTaskModal'));
    }

    async loadScripts() {
        try {
            const result = await api.getScripts();
            const select = document.getElementById('scriptPath');
            select.innerHTML = '<option value="">请选择脚本</option>';

            if (result.code === 'success') {
                result.data.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.path;
                    option.text = item.name;
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error('加载脚本失败:', e);
        }
    }

    showAdd() {
        this.isEditMode = false;
        document.getElementById('addTaskForm').reset();
        document.getElementById('editTaskId').value = '';
        document.querySelector('#addTaskModal .modal-title').innerHTML = '<i class="bi bi-plus-circle me-2"></i>添加新任务';
        this.modal.show();
    }

    async showEdit(taskId) {
        this.isEditMode = true;

        try {
            // 先从服务端获取最新的任务信息
            const result = await api.getTask(taskId);

            if (result.code !== 'success' || !result.data) {
                alert('获取任务信息失败');
                return;
            }

            const task = result.data;

            // 等待脚本列表加载完成后再设置表单值
            await this.loadScripts();

            document.getElementById('editTaskId').value = taskId;
            document.getElementById('taskName').value = task.name;
            document.getElementById('scriptPath').value = task.script_path;
            document.getElementById('triggerType').value = task.trigger_type;
            document.getElementById('taskDescription').value = task.description || '';

            // 设置触发参数
            if (task.trigger_type === 'interval') {
                document.getElementById('triggerArgs').value = JSON.stringify({seconds: task.interval_seconds});
            } else if (task.trigger_type === 'cron') {
                document.getElementById('triggerArgs').value = task.cron_expression || '';
            }

            document.querySelector('#addTaskModal .modal-title').innerHTML = '<i class="bi bi-pencil me-2"></i>编辑任务';
            this.modal.show();
        } catch (e) {
            console.error('编辑任务失败:', e);
            alert('获取任务信息失败');
        }
    }

    hide() {
        this.modal.hide();
    }

    async submit() {
        const editId = document.getElementById('editTaskId').value;
        const name = document.getElementById('taskName').value.trim();
        const scriptPath = document.getElementById('scriptPath').value;
        const triggerType = document.getElementById('triggerType').value;
        const triggerArgsStr = document.getElementById('triggerArgs').value.trim();
        const description = document.getElementById('taskDescription').value.trim();

        if (!name || !scriptPath) {
            alert('请填写任务名称和选择脚本');
            return;
        }

        let triggerArgs = {};
        if (triggerArgsStr) {
            try {
                triggerArgs = JSON.parse(triggerArgsStr);
            } catch (e) {
                alert('触发参数格式错误，请输入有效的JSON');
                return;
            }
        }

        try {
            let result;
            if (editId) {
                // 编辑模式
                result = await api.updateTask(editId, {
                    name,
                    script_path: scriptPath,
                    trigger_type: triggerType,
                    cron_expression: triggerType === 'cron' ? triggerArgsStr : null,
                    interval_seconds: triggerType === 'interval' ? (triggerArgs.seconds || 60) : null,
                    arguments: [],
                    working_directory: null,
                    timeout: 300,
                    description
                });
            } else {
                // 新增模式
                result = await api.createTask({
                    task_name: name,
                    func_name: scriptPath,
                    trigger_type: triggerType,
                    trigger_args: triggerArgs,
                    args: [],
                    script_path: scriptPath,
                    cron_expression: triggerType === 'cron' ? triggerArgsStr : null,
                    interval_seconds: triggerType === 'interval' ? (triggerArgs.seconds || 60) : null,
                    arguments: [],
                    working_directory: null,
                    timeout: 300,
                    enabled: false,
                    description
                });
            }

            if (result.code === 'success') {
                this.hide();
                if (this.onSave) {
                    this.onSave();
                }
            } else {
                alert('操作失败: ' + (result.message || '未知错误'));
            }
        } catch (e) {
            console.error(e);
            alert('请求失败');
        }
    }

    updateTriggerPlaceholder() {
        const type = document.getElementById('triggerType').value;
        const hint = document.getElementById('triggerHint');
        const args = document.getElementById('triggerArgs');

        if (type === 'interval') {
            args.placeholder = '{"seconds": 60}';
            hint.textContent = '间隔执行，单位：秒';
        } else if (type === 'cron') {
            args.placeholder = '{"hour": 14, "minute": 30}';
            hint.textContent = '定时执行，时:分';
        } else {
            args.placeholder = '{"run_date": "2024-12-31 14:30:00"}';
            hint.textContent = '单次执行，指定日期时间';
        }
    }
}
