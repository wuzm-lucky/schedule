/**
 * 任务列表组件
 */

import { api } from './api.js';

export class TaskList {
    constructor(container) {
        this.container = container;
        this.allTasks = [];
        this.currentFilter = 'all';
        this.selectedTaskId = null;
        this.onTaskSelect = null;
    }

    setTasks(tasks) {
        this.allTasks = tasks;
        this.render();
        this.updateCounts();
    }

    setFilter(filter) {
        this.currentFilter = filter;
        this.render();
    }

    filterTasks(keyword) {
        this.render(keyword);
    }

    selectTask(taskId) {
        this.selectedTaskId = taskId;
        this.render();
        if (this.onTaskSelect) {
            this.onTaskSelect(taskId);
        }
    }

    updateCounts() {
        const countAll = document.getElementById('count-all');
        const countEnabled = document.getElementById('count-enabled');
        const countDisabled = document.getElementById('count-disabled');

        if (countAll) countAll.textContent = this.allTasks.length;
        if (countEnabled) countEnabled.textContent = this.allTasks.filter(t => t.enabled).length;
        if (countDisabled) countDisabled.textContent = this.allTasks.filter(t => !t.enabled).length;
    }

    render(keyword = '') {
        let tasks = [...this.allTasks];

        // 应用筛选
        if (this.currentFilter === 'enabled') {
            tasks = tasks.filter(t => t.enabled);
        } else if (this.currentFilter === 'disabled') {
            tasks = tasks.filter(t => !t.enabled);
        }

        // 应用搜索
        if (keyword) {
            tasks = tasks.filter(t => t.name.toLowerCase().includes(keyword.toLowerCase()));
        }

        if (tasks.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>暂无任务</p>
                </div>
            `;
            return;
        }

        this.container.innerHTML = tasks.map(task => this.renderTaskCard(task)).join('');
    }

    renderTaskCard(task) {
        const isEnabled = task.enabled;
        const triggerInfo = this.getTriggerInfo(task);

        return `
            <div class="task-card ${!isEnabled ? 'disabled' : ''} ${this.selectedTaskId === task.id ? 'selected' : ''}"
                 onclick="window.taskList.selectTask('${task.id}')">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="task-name">
                            ${isEnabled ?
                                '<i class="bi bi-play-circle-fill text-success me-1"></i>' :
                                '<i class="bi bi-pause-circle text-warning me-1"></i>'}
                            ${this.escapeHtml(task.name)}
                        </div>
                        <div class="task-meta">
                            <span class="badge bg-secondary">${task.trigger_type}</span>
                            ${triggerInfo}
                            ${task.next_run_time ? `<span class="ms-2"><i class="bi bi-clock"></i> ${this.formatTime(task.next_run_time)}</span>` : ''}
                        </div>
                        <div class="task-stats">
                            <span class="stat-item stat-total">
                                <i class="bi bi-arrow-repeat"></i> ${task.run_count || 0}
                            </span>
                            <span class="stat-item stat-success">
                                <i class="bi bi-check-circle"></i> ${task.success_count || 0}
                            </span>
                            <span class="stat-item stat-failed">
                                <i class="bi bi-x-circle"></i> ${task.failed_count || 0}
                            </span>
                        </div>
                    </div>
                    <div class="task-actions" onclick="event.stopPropagation()">
                        ${isEnabled ?
                            `<button class="btn btn-warning btn-sm" onclick="window.app.pauseTask('${task.id}')" title="暂停">
                                <i class="bi bi-pause"></i>
                            </button>` :
                            `<button class="btn btn-success btn-sm" onclick="window.app.resumeTask('${task.id}')" title="启用">
                                <i class="bi bi-play"></i>
                            </button>`
                        }
                        ${!isEnabled ?
                            `<button class="btn btn-info btn-sm" onclick="window.app.editTask('${task.id}')" title="编辑">
                                <i class="bi bi-pencil"></i>
                            </button>` : ''
                        }
                        <button class="btn btn-primary btn-sm" onclick="window.app.runTask('${task.id}')" title="立即执行">
                            <i class="bi bi-play-fill"></i>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="window.app.deleteTask('${task.id}')" title="删除">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    getTriggerInfo(task) {
        if (task.trigger_type === 'cron') {
            return `<code>${this.escapeHtml(task.cron_expression || '')}</code>`;
        } else if (task.trigger_type === 'interval') {
            return `每 ${task.interval_seconds} 秒`;
        }
        return '';
    }

    formatTime(timeStr) {
        if (!timeStr) return '-';
        const date = new Date(timeStr);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return '即将执行';
        if (diff < 3600000) return Math.floor(diff / 60000) + '分钟后';
        if (diff < 86400000) return Math.floor(diff / 3600000) + '小时后';

        return date.toLocaleString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
