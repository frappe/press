---
route: servers/database-replication-new
allow_guest: 1
published: 1
---

> Note: This will wipe data already present on the secondary Database Server.

#### Requires 
- Primary and secondary Database Servers should be already setup.

#### Steps

1. Set **Primary** field on the secondary Database Server


![](../files/primary-set.png)

1. On Secondary Database Server Click on **Actions > Setup Replication**


![](../files/database-server-actions.png)
 This runs playbooks on both primary and secondary Database Server.


1. Setup Complete

 **Replication Setup** field on secondary Database Server will be set.


![](../files/replication-complete.png)