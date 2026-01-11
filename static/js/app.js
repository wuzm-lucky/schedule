/**
 * 主应用模块
 * 协调各组件工作
 */

import { api } from './api.js';
import { TaskList } from './task-list.js';
import { ExecutionLog } from './execution-log.js';
import { TaskModal } from './task-modal.js';

class ScheduleApp {
    constructor() {
        this.taskList = null;
        this.executionLog = null;
        this.taskModal = null;
        this.refreshTimer = null;
    }

    async init() {
        // 初始化组件
        this.taskList = new TaskList(document.getElementById('taskList'));
        this.executionLog = new ExecutionLog(document.getElementById('executionLog'));
        this.taskModal = new TaskModal();
        await this.taskModal.init();

        // 设置事件绑定
        this.bindEvents();

        // 设置任务列表回调
        this.taskList.onTaskSelect = (taskId) => {
            this.onTaskSelect(taskId);
        };

        // 加载数据
        await this.loadTasks();

        // 设置定时刷新
        this.refreshTimer = setInterval(() => {
            this.loadTasks(false);
            if (this.taskList.selectedTaskId) {
                this.executionLog.loadExecutions(this.taskList.selectedTaskId);
            }
        }, 30000);
    }

    bindEvents() {
        // 筛选按钮
        document.querySelectorAll('[data-filter]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setFilter(btn.dataset.filter);
            });
        });

        // 搜索框
        document.getElementById('searchInput').addEventListener('keyup', () => {
            this.taskList.filterTasks(document.getElementById('searchInput').value);
        });

        // 刷新按钮
        document.querySelector('[onclick="loadTasks()"]')?.addEventListener('click', (e) => {
            e.target.onclick = null;  // 移除内联事件
            this.loadTasks();
        });

        // 添加任务按钮
        document.querySelector('[onclick="showAddModal()"]')?.addEventListener('click', (e) => {
            e.target.onclick = null;
            this.showAddModal();
        });

        // 触发器类型变更
        document.getElementById('triggerType')?.addEventListener('change', () => {
            this.taskModal.updateTriggerPlaceholder();
        });

        // 保存任务按钮
        document.querySelector('[onclick="submitTask()"]')?.addEventListener('click', (e) => {
            e.target.onclick = null;
            this.taskModal.submit();
        });

        // 暴露到全局供 HTML 调用
        window.app = this;
        window.taskList = this.taskList;
        window.loadScripts = () => this.taskModal.loadScripts();
        window.loadTasks = (showLoading = true) => this.loadTasks(showLoading);
        window.setFilter = (filter) => this.setFilter(filter);
        window.filterTasks = () => this.taskList.filterTasks(document.getElementById('searchInput').value);
        window.showAddModal = () => this.showAddModal();
        window.submitTask = () => this.taskModal.submit();
        window.updateTriggerPlaceholder = () => this.taskModal.updateTriggerPlaceholder();
    }

    async loadTasks(showLoading = true) {
        try {
            const result = await api.getTasks();

            if (result.code === 'success') {
                this.taskList.setTasks(result.data);
            }
        } catch (e) {
            console.error('加载任务失败:', e);
        }
    }

    setFilter(filter) {
        this.taskList.setFilter(filter);

        document.querySelectorAll('[data-filter]').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.filter === filter) {
                btn.classList.add('active');
            }
        });
    }

    onTaskSelect(taskId) {
        const task = this.taskList.allTasks.find(t => t.id === taskId);
        const taskNameEl = document.getElementById('selectedTaskName');
        if (taskNameEl) {
            taskNameEl.textContent = task ? task.name : '请选择任务';
        }
        this.executionLog.loadExecutions(taskId);
    }

    showAddModal() {
        this.taskModal.showAdd();
    }

    editTask(taskId) {
        this.taskModal.showEdit(taskId);
    }

    async deleteTask(taskId) {
        if (!confirm('确定要删除此任务吗？删除后可以恢复。')) return;

        try {
            const result = await api.deleteTask(taskId);
            if (result.code === 'success') {
                this.loadTasks();
                if (this.taskList.selectedTaskId === taskId) {
                    this.taskList.selectedTaskId = null;
                    this.executionLog.showEmpty('点击任务查看执行记录');
                    document.getElementById('selectedTaskName').textContent = '请选择任务';
                }
            }
        } catch (e) {
            console.error(e);
            alert('删除失败');
        }
    }

    async pauseTask(taskId) {
        try {
            const result = await api.pauseTask(taskId);
            if (result.code === 'success') {
                this.loadTasks();
            }
        } catch (e) {
            console.error(e);
        }
    }

    async resumeTask(taskId) {
        try {
            const result = await api.resumeTask(taskId);
            if (result.code === 'success') {
                this.loadTasks();
            }
        } catch (e) {
            console.error(e);
        }
    }

    async runTask(taskId) {
        if (!confirm('确定要立即执行此任务吗？')) return;

        try {
            const result = await api.runTask(taskId);
            if (result.code === 'success') {
                if (this.taskList.selectedTaskId === taskId) {
                    setTimeout(() => {
                        this.executionLog.loadExecutions(taskId);
                    }, 1000);
                }
            } else {
                alert(result.message);
            }
        } catch (e) {
            console.error(e);
            alert('执行失败');
        }
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', function() {
    window.appInstance = new ScheduleApp();
    window.appInstance.init();
});
