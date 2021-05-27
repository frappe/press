---
title: "Guide: Local Development Enviroment Setup"
---

# Local Development Environment Setup

This guide shows you how to setup your development machine for Frappe Cloud development. By the end of this guide, you will have a replica of the FC production environment.

> “Patience is bitter, but its fruit is sweet.” – Aristotle

## Introduction

`f` servers: These host your benches (`f` is for Frappe Apps)

`m` servers: These host the database (`m` is for MariaDB)

`n` servers: These are proxy servers (`n` is Nginx, which does the proxying)

## Prerequisites

### Softwares

You should have the following software packages installed on your computer before proceeding:

1. Docker: Latest, don't forget to give `docker` sudo access!

2. Certbot: Latest

3. dns-route53 plugin for certbot: `pip3 install certbot-dns-route53`

### Credentials from Frappe Assets

You will need access to the following credentials, which you can find in `Frappe Assets` at frappe.io:

1. Hetzner

2. Digital Ocean

3. AWS

## Creating Servers on Hetzner

[Hetzner](https://www.hetzner.com/) is a cloud hosting provider that we will use to create our servers (`n`, `f` and `m`). In production, we use digital ocean but for development purposes, hetzner is a better value for money.

The naming convention used can be seen in the servers list:

`<server-type><server-number>.<name-initial>.fc.frappe.dev`

For example, f1.g.fc.frappe.dev is the first `f` server and `g` is for Gavin.

Create a Network while creating the first server and choose that network for other two servers also. Don't forget to add your public SSH keys during server creation.

Now, create 3 servers in `Helsinki` region and with `Ubuntu 20.04` OS:

1. `n1.<unique-name-initial>.fc.frappe.dev`: CX11 type.

2. `f1.<unique-name-initial>.fc.frappe.dev`: CX21 type.

3. `m1.<unique-name-initial>.fc.frappe.dev`: CX21 type.

Note down the IP Address of all the three servers.

## Creating DNS records in AWS Route53

Go to the AWS Console (again, credentials are in Frappe Assets), navigate to `Route 53 > Hosted Zones`. Click on `fc.frappe.dev` domain name. You have to create 4 DNS `A` records here. One record will be a wild-card sub-domain:

`*.<name-initial>.fc.frappe.dev` pointing to the IP address of the `n` server created in the previous section.

The other 3 records will be for f1, n1 and m1 respectively. Use the IP address from the previous step. You can have a look at other such records if you get confused at any point.

Now, make sure you can `ssh` (as `root`) into all the three servers using thier domain names. For example:

```bash
> ssh root@f1.h.fc.frappe.dev
```

## Press Frappe App

On your computer, `get-app` press using this [GitHub URL](https://github.com/frappe/press). Now, create a new site and install `press` on this site.

Run the site and login as admin. (Login ID and password are `admininstrator` and `admin` respectively)

## Press Settings

### Create a `Root Domain`

Navigate to `Root Domain List` (AwesomeBar to rescue!) and create a new document. Fill up the details as below:

Name: `<your-domain-name>`, e.g. `h.fc.frappe.dev`
Default CLuster: `Default`
AWS Access Key ID: Get from `AWS Console`
AWS Secret Access Key: Get from `AWS Console`

Save it.

Open `Press Settings` now. Now, set the `Domain` to the root domain you created in the previous step and cluster to `Default`.

Now, there is going to be a lot of back and forth between your terminal and `Press Settings`, so sit tight.

### Let's Encrypt

Scroll down and expand the `Let's Encrypt` section. Before entering the details here, you have to create two directories on your local computer (it is better to place this at user level, e.g. `/home/<user>/`):

1. `.certbot` -> directory
2. `webroot` -> directory, inside the .certbot directory

Now, fill the `Certbot Directory` and `Webroot Directory` with the absolute path of the above two newly created directories respectively. Leave out other fields as it is. You can enter your email if you want.

Save the settings.

### Docker

Now, Scroll down to `Docker Registry` section.

Fill in the fields as given below:

`Docker Registry URL`: registry.digitalocean.com/staging-frappe-cloud

`Docker Registry Namespace`: Any name you like, e.g. `hussain-staging`

`Docker Registry Username`: Get from Digital Ocean account or contact `@kawaiideku`

`Docker Registry Password`: Get from Digital Ocean account or contact `@kawaiideku`

Again, save the settings and scroll down to `Docker Build` section.

Go to your terminal and `cd` into your `bench` directory. Create two directories here:

1. `.clones`
2. `.docker-builds`

Go back to the `Press Settings`and paste the absolute paths of the above two directories to the `Clone Directory` and `Build Directory` respectively. Leave the other field empty and save the settings.

Sometimes, there is an issue while uploading a docker image in the background and you have to manually `push` it to registry. For that case, you have to login to digital ocean registry through docker before pushing. You can do this by running this command:

```bash
> docker login -u <do-registry-user-id> -p <do-password> registry.digitalocean.com
```

## Setting up Proxy server (`n` server)

Go to the `Proxy Server` list and click `+ Add Proxy Server`. Fill in the details as given below:

Hostname: `n1` (`n2`, `n3`, if you want to create more Proxy servers)

IP: IP Address of the `n` server.
Private IP: Private (internal) IP Address of the `n` server. Can be found in `Hetzner` console.

Click on save.

> Note: The agent password will be set automatically for you.

Now, click on the `Actions` dropdown button, which is located next to the `Save` button and click on `Setup Server`. The server should go in `Installing` state.

This will setup the server. We use `Ansible` to automate the infrastructure, so, once you click on the `Setup Server` button, `Ansible Play`s will be created and run in the background to setup the server (install necessary software, perform essential configuration changes and more). Each `Ansible Play` document creates a number of `Ansible Task`, which is an individual task that will be carried out to setup the server.

Navigate to `Ansible Task List` and you should see some tasks which will have a particular status. For example, `success` means the task completed successfully and `running` means the task is currently running. You should confirm that all the tasks are eventually `success`ful.

After some time, when the tasks have completed to run, the `Proxy Server` will go to `Active` state.

If there is any error (for example, if the `Proxy Server` goes into `Broken` state) or a task keeps running forever, go to the `Error Log List` and you will most probably find a log that corresponds to the task and more information on why it failed.

## Setting up DB server (`m` server)

In this section, we will move on to create a `Database Server`. Go to the `Database Server List` and create a new document. Fill in the fields as given below:

Hostname: `m1`
IP: External IP address of the `m` server
Private IP: Internal IP address of the `m` server

MariaDB Root Password: Create a password, this will be the `root` password of the MariaDB database that will be installed on this server.

Now, you have to follow the same steps as for the proxy server. Save the document and do setup server. Once this server is setup, you can move on to setting up the `f` server.

## Setting up App server (`f` server)

In the proxy server section, we created and set up the `Proxy Server` which sits in the front and forwards traffic to various `f` servers. Now, `f` servers are where the benches (along with the sites) are present. The databases are on different `m` servers and the sites hosted in the `f` servers use those databases.

Go to the `Server List` and add a new server document. Fill in the details as given below:

Hostname: `f1`
Cluster: `Default`

IP: External IP address of `f` server
Private IP: Internal IP address of `f` server

Proxy Server: Select the `Proxy Server` which we created in a previous section.
Database Server: Select the `Database Server` which we created in the previous section.

Leave other fields as they are.

Now, again the same process: save and setup!

## Creating Your First Site

### Creating an App

The first step is to create an App that will ultimately be installed on our site. The first app in any release group must be `frappe` (Frappe Framework), the name is case sensitive. Navigate to `App List` page and click on `'+ Add new App'` button on the top-right corner. Fill in the details as below:

![New App](/assets/press/images/internal/setup/new_app.png)

### Create App Source

Now, we need to create an App source for this app. Navigate to `App Source` list page, create a new document and fill in the details as below:

![New App](/assets/press/images/internal/setup/new_app_source.png)

### Creating a Release Group

Navigate to the `Release Group` list and create a new release group. The details to be filled are shown in the screenshot below.

![New App](/assets/press/images/internal/setup/new_release_group.png)

Select the app source that you created in the previous step. Click save.

Once you save the release group document, a `Deploy Candidate` is automatically created for this release group. In fact, a deploy candidate is created any time you make changes to the `Release Group`.

![New App](/assets/press/images/internal/setup/release_group_saved.png)

Click on the `Deploy Candidate` chip and this will take you to the `Deploy Candidate` page which is filtered for the current `Release Group`. Select the `Deploy Candidate` (are named like `bench-xxx`) that was created latest. You should only have one if you never created a release group before. Now, click on `Actions` and then `Build and Deploy`.

![New App](/assets/press/images/internal/setup/deploy_candidate.png)

This will build the docker image for this bench, upload it to the digital ocean image registry and also deploy it to your `f` server.

You can click on `Visit Dashboard` link on the top-left corner to view the progress of the build and deploy step.

Once the image is deployed, you can go the benches list and you will find a new bench there. This was created using the `Deploy Candidate`. Now, you can go ahead and create as many sites you want. You can do this either via the dashboad or the desk.

## Resolving issues

One of the issues that you may get into is not being able to obtain a TLS Certificate for the root domain. If that is the case, you have to manually call (via `console`) the `_obtain_certificate` method on the `TLS Certificate Document` that was created for the `Root Domain` document that we created in the initial part of this guide.


## Conclusion

If you made till here, well done and be proud of yourself. Now, its time to build awesome things. Good Luck with your journey on Frappe Cloud.
