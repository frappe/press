This folder holds the library / tools written for Press or agent.

Please check the `README.md` of the library / tool for more details.

| Library / Tool           | Description                                                                                     | Documentation                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| File Warmer              | Helps to pre-warm specific files of volume                                                      | [Read More](./filewarmer/README.md)                          |
| Binlog Indexer           | Index binlogs and provide faster search                                                         | [Read More](./mariadb_binlog_indexer/README.md)              |
| ProxySQL Filebeat Module | Parse ProxySQL Audit + Event Logs via Filebeat                                                  | [Source](../press/playbooks/roles/filebeat/module/proxysql/) |
| FC Restore CLI           | Minimal CLI to restore/migrate big sites                                                        | [Source](./fcrestore/)                                       |
| MariaDB IO Monitor       | CLI to trace mariadb's file access and gather important information in incident                 | [Read More](./mariadb_io_monitor/README.md)                  |
| MariaDB Monitor          | Daemon service to monitor system health and detect anomaly and help in mariadb recovery | [Read More](./mariadb_monitor/README.md)                     |
