-- ===========================
-- 1. 创建数据库
-- ===========================
CREATE DATABASE IF NOT EXISTS `scheduler`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE `scheduler`;

-- ===========================
-- 2. 任务配置表
-- 对应 Python 代码中的 models.py -> Task
-- ===========================
CREATE TABLE IF NOT EXISTS `tasks` (
    `id` VARCHAR(191) NOT NULL COMMENT '任务ID',
    `name` VARCHAR(200) NOT NULL COMMENT '任务名称',
    `script_path` VARCHAR(500) NOT NULL COMMENT '脚本路径',
    `trigger_type` VARCHAR(20) NOT NULL COMMENT '触发器类型: cron/interval/date',
    `cron_expression` VARCHAR(100) DEFAULT NULL COMMENT 'Cron表达式',
    `interval_seconds` INT DEFAULT NULL COMMENT '间隔秒数',
    `scheduled_time` DATETIME DEFAULT NULL COMMENT '指定执行时间',
    `arguments` JSON DEFAULT NULL COMMENT '脚本参数',
    `working_directory` VARCHAR(500) DEFAULT NULL COMMENT '工作目录',
    `environment` JSON DEFAULT NULL COMMENT '环境变量',
    `timeout` INT DEFAULT 300 COMMENT '超时时间(秒)',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `description` TEXT DEFAULT NULL COMMENT '任务描述',
    `notification_enabled` BOOLEAN DEFAULT FALSE COMMENT '是否启用通知',
    `notification_config` JSON DEFAULT NULL COMMENT '通知配置',
    `run_count` INT DEFAULT 0 COMMENT '运行次数',
    `success_count` INT DEFAULT 0 COMMENT '成功次数',
    `failed_count` INT DEFAULT 0 COMMENT '失败次数',
    `deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除(逻辑删除)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_deleted` (`deleted`),
    INDEX `idx_trigger_type` (`trigger_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===========================
-- 3. APScheduler 持久化表
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
-- 4. 任务执行日志表
-- 对应 Python 代码中的 models.py -> TaskExecution
-- ===========================
CREATE TABLE IF NOT EXISTS `task_executions` (
    `id` VARCHAR(191) NOT NULL COMMENT '执行ID',
    `task_id` VARCHAR(191) NOT NULL COMMENT '任务ID',
    `task_name` VARCHAR(200) DEFAULT NULL COMMENT '任务名称',
    `status` VARCHAR(20) NOT NULL COMMENT '执行状态: pending/running/success/failed/timeout/cancelled',
    `start_time` DATETIME NOT NULL COMMENT '开始时间',
    `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
    `duration` FLOAT DEFAULT NULL COMMENT '耗时(秒)',
    `exit_code` INT DEFAULT NULL COMMENT '退出码',
    `output` TEXT DEFAULT NULL COMMENT '标准输出',
    `error` TEXT DEFAULT NULL COMMENT '错误信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
