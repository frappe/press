---
title: Server Setup - Server
---

# Server Setup
Server runs benches as well as its own MariaDB database.

> Note: [Proxy Server Setup](/internal/servers/proxy-server-setup) must be completed before Server setup.

#### Requires 
- Press host must have root SSH access to the target machine.

#### Steps

1. Create a Server Document and Save
![New Server Document](/assets/press/images/internal/servers/server/new-server.png)

1. Click on **Actions > Setup Server**

 ![New Server Document](/assets/press/images/internal/servers/server/setup-server-actions.png)

During the playbook execution, Server status is set as **Installing**.

 ![Setup Server Installing](/assets/press/images/internal/servers/server/setup-server-installing.png)

> Note: Running a playbook blocks a worker for the duration of the play.

Setup Server action runs an Ansible playbook. The status of the play is tracked in Ansible Play and the tasks in the play are tracked in Ansible Task. play and task updates are reflected in realtime.

 ![Setup Server Play Running List](/assets/press/images/internal/servers/server/setup-server-play-running-list.png)

 ![Setup Server Play Running](/assets/press/images/internal/servers/server/setup-server-play-running.png)

 ![Setup Server Tasks Running](/assets/press/images/internal/servers/server/setup-server-tasks-running.png)

 ![Setup Server Task Success](/assets/press/images/internal/servers/server/setup-server-task-success.png)

 ![Setup Server Tasks Complete](/assets/press/images/internal/servers/server/setup-server-tasks-complete.png)

 ![Setup Server Play Success](/assets/press/images/internal/servers/server/setup-server-play-success.png)


 ![Setup Server Success](/assets/press/images/internal/servers/server/setup-server-success.png)

Once the playbook execution is complete, If failed, Server status is set as **Broken**. The Server setup can be retried with **Actions > Setup Server**.

If successful, Server status is set as **Active** and **Server Setup** field is checked. 


### Add Server to Proxy

This adds the Server as an NGINX upstream on the Proxy Server. This action is carried out using Agent. The status of this job can be tracked under Add Upstream to Proxy Agent Job. If successful, the **Upstream Setup** field is checked.

1. Set **Proxy Server** field and Save.

 ![Setup Server Set Proxy](/assets/press/images/internal/servers/server/setup-server-set-proxy.png)

1. Click **Actions > Add To Proxy**

 ![Setup Server Add To Proxy](/assets/press/images/internal/servers/server/setup-server-actions-add-to-proxy.png)

 ![Add Upstream To Proxy Job](/assets/press/images/internal/servers/server/add-upstream-to-proxy-job.png)
