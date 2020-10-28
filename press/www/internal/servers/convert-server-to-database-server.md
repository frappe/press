---
title: Convert Frappe Server to Database Server
---

# Convert Frappe Server to Database Server

> Note: Downtime Ahead! This will restart MariaDB process.

Convert a Server into a Database Server, So that, a local database can be moved to a remote server using MariaDB replication.

> Note: MariaDB running on a Server allows clients to connect from localhost only. MariaDB running on Database Server allows clients to connect from the private network.

#### Requires 
- Press host must have root SSH access to the target machine.

#### Steps

1. Create a Database Server
 - Use all values from the Server as-is.
 - Set unique **Server ID** (a unique value will be set if not left unset).

 ![Server](/assets/press/images/internal/servers/convert-frappe-to-database/server.png)

 ![New Database Server](/assets/press/images/internal/servers/convert-frappe-to-database/new-database-server.png)

1. Click on **Actions > Convert From Frappe Server**

 ![Convert From Frappe Server](/assets/press/images/internal/servers/convert-frappe-to-database/database-server-actions-convert.png)

1. Setup Complete

 **Database Server** field on the Server will be set. (As if the MariaDB is hosted remotely).

 ![Database Server Active](/assets/press/images/internal/servers/convert-frappe-to-database/database-server-active.png)

 ![Server Active](/assets/press/images/internal/servers/convert-frappe-to-database/server-active.png)
