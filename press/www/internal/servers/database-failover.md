---
title: Database Failover - Server
---

# Database Failover

> Note: Minor Downtime + Data Loss ahead!

#### Requires 
- [Database Replication](/internal/servers/database-replication) should be already setup.

#### Steps

1. On Secondary Database Server Click on **Actions > Trigger Failover**

 This doesn't require the primary Database Server to be online. 

 ![Setup Replication](/assets/press/images/internal/servers/database-failover/database-server-actions-failover.png)


1. Failover Complete

 **Database Server** field will be updated on all Servers and Benches linked to the primary Database Server.

 ![Server After](/assets/press/images/internal/servers/database-failover/server-after.png)

 ![Bench After](/assets/press/images/internal/servers/database-failover/bench-after.png)

 Database Server will be promoted to primary.

 ![Database Server After](/assets/press/images/internal/servers/database-failover/database-server-after.png)

