/**
 * 执行记录日志组件
 */

import { api } from './api.js';

export class ExecutionLog {
    constructor(container) {
        this.container = container;
        this.currentTaskId = null;
    }

    async loadExecutions(taskId) {
        this.currentTaskId = taskId;

        if (!taskId) {
            this.showEmpty('点击任务查看执行记录');
            return;
        }

        try {
            const result = await api.getTaskExecutions(taskId, 50);

            if (result.code === 'success') {
                if (result.data.length === 0) {
                    this.showEmpty('暂无执行记录');
                    return;
                }
                this.render(result.data);
            }
        } catch (e) {
            console.error('加载执行记录失败:', e);
            this.showEmpty('加载失败');
        }
    }

    showEmpty(message) {
        this.container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-terminal"></i>
                <p>${message}</p>
            </div>
        `;
    }

    render(executions) {
        this.container.innerHTML = executions.map(log => this.renderLogEntry(log)).join('');
    }

    renderLogEntry(log) {
        const statusClass = log.status === 'success' ? 'log-success' :
                           log.status === 'failed' ? 'log-failed' : 'log-running';
        const statusIcon = log.status === 'success' ? 'check-circle' :
                          log.status === 'failed' ? 'x-circle' : 'arrow-repeat';

        return `
            <div class="log-entry">
                <div>
                    <span class="log-time">${this.formatTime(log.start_time)}</span>
                    <span class="${statusClass}">
                        <i class="bi bi-${statusIcon}"></i> ${log.status.toUpperCase()}
                    </span>
                    ${log.duration ? `<span class="text-muted"> | 耗时 ${log.duration?.toFixed(2)}s</span>` : ''}
                </div>
                ${log.output ? `<div class="text-muted mt-1">${this.escapeHtml(log.output.substring(0, 200))}</div>` : ''}
                ${log.error ? `<div class="text-danger mt-1">${this.escapeHtml(log.error.substring(0, 200))}</div>` : ''}
            </div>
        `;
    }

    formatTime(timeStr) {
        if (!timeStr) return '-';
        return new Date(timeStr).toLocaleString('zh-CN');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
