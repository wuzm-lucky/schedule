/**
 * API 模块
 * 封装所有后端 API 调用
 */

const API_BASE = '/api';

export const api = {
    // ========== 任务相关 ==========
    async getTasks(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`${API_BASE}/tasks?${query}`);
        return await res.json();
    },

    async getTask(taskId) {
        const res = await fetch(`${API_BASE}/tasks/${taskId}`);
        return await res.json();
    },

    async createTask(data) {
        const res = await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return await res.json();
    },

    async updateTask(taskId, data) {
        const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return await res.json();
    },

    async deleteTask(taskId) {
        const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
            method: 'DELETE'
        });
        return await res.json();
    },

    async restoreTask(taskId) {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/restore`, {
            method: 'POST'
        });
        return await res.json();
    },

    async pauseTask(taskId) {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/pause`, {
            method: 'POST'
        });
        return await res.json();
    },

    async resumeTask(taskId) {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/resume`, {
            method: 'POST'
        });
        return await res.json();
    },

    async runTask(taskId) {
        const res = await fetch(`${API_BASE}/tasks/run/${taskId}`, {
            method: 'POST'
        });
        return await res.json();
    },

    async getTaskExecutions(taskId, limit = 50, status = null) {
        let url = `${API_BASE}/tasks/${taskId}/executions?limit=${limit}`;
        if (status) url += `&status=${status}`;
        const res = await fetch(url);
        return await res.json();
    },

    // ========== 脚本相关 ==========
    async getScripts() {
        const res = await fetch(`${API_BASE}/scripts`);
        return await res.json();
    },

    // ========== 健康检查 ==========
    async healthCheck() {
        const res = await fetch(`${API_BASE}/health`);
        return await res.json();
    }
};
