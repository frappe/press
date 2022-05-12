DROP DATABASE IF EXISTS `percona`;

CREATE DATABASE `percona` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `percona`;

DROP TABLE IF EXISTS `deadlock`;

CREATE TABLE `deadlock` (
    `server` char(20) NOT NULL,
    `ts` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `thread` int unsigned NOT NULL,
    `txn_id` bigint unsigned NOT NULL,
    `txn_time` smallint unsigned NOT NULL,
    `user` char(16) NOT NULL,
    `hostname` char(20) NOT NULL,
    `ip` char(15) NOT NULL,
    `db` char(64) NOT NULL,
    `tbl` char(64) NOT NULL,
    `idx` char(64) NOT NULL,
    `lock_type` char(16) NOT NULL,
    `lock_mode` char(1) NOT NULL,
    `wait_hold` char(1) NOT NULL,
    `victim` tinyint unsigned NOT NULL,
    `query` text NOT NULL,
    PRIMARY KEY (`server`, `ts`, `thread`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
