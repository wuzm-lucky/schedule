	-- ===========================
	-- 1. 创建数据库
	-- ===========================
	CREATE DATABASE IF NOT EXISTS `task_scheduler`
	    DEFAULT CHARACTER SET utf8mb4
	    COLLATE utf8mb4_unicode_ci;
	USE `task_scheduler`;
	-- ===========================
	-- 2. APScheduler 持久化表
	-- 注意：如果使用 SQLAlchemyJobStore，APScheduler 会自动管理此表，
	-- 但手动创建可以确保权限和结构符合预期。
	-- ===========================
	CREATE TABLE IF NOT EXISTS `apscheduler_jobs` (
	    `id` VARCHAR(191) NOT NULL,
	    `next_run_time` DECIMAL(26, 6) DEFAULT NULL,
	    `job_state` LONGBLOB NOT NULL,
	    PRIMARY KEY (`id`),
	    INDEX `idx_next_run_time` (`next_run_time`)
	) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
	-- ===========================
	-- 3. 任务执行日志表
	-- 对应 Python 代码中的 models.py -> TaskLog
	-- ===========================
	CREATE TABLE IF NOT EXISTS `task_logs` (
	    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
	    `job_id` VARCHAR(100) NOT NULL COMMENT '任务ID (关联 apscheduler_jobs)',
	    `job_name` VARCHAR(200) DEFAULT NULL COMMENT '任务名称',
	    `status` VARCHAR(20) NOT NULL COMMENT '执行状态: success/failed/missed',
	    `run_time` DATETIME NOT NULL COMMENT '执行时间',
	    `duration` FLOAT DEFAULT NULL COMMENT '耗时(秒)',
	    `result` TEXT COMMENT '执行结果或异常堆栈信息',
	    PRIMARY KEY (`id`),
	    INDEX `idx_job_id` (`job_id`), -- 优化根据任务ID查询日志的性能
	    INDEX `idx_run_time` (`run_time`) -- 优化按时间倒序查询日志的性能
	) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;