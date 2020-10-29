---
title: Database Replication - Server
---

# Database Replication

> Note: This will wipe data already present on the secondary Database Server.

#### Requires 
- Primary and secondary Database Servers should be already setup.

#### Steps

1. Set **Primary** field on the secondary Database Server

 ![Server](/assets/press/images/internal/servers/database-replication/primary-set.png)

1. On Secondary Database Server Click on **Actions > Setup Replication**

 ![Setup Replication](/assets/press/images/internal/servers/database-replication/database-server-actions.png)

 This runs playbooks on both primary and secondary Database Server.

 ![Multiple Plays](/assets/press/images/internal/servers/database-replication/multiple-plays.png)


1. Setup Complete

 **Replication Setup** field on secondary Database Server will be set.

 ![Server Active](/assets/press/images/internal/servers/database-replication/replication-complete.png)
