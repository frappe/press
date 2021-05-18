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

## Setting up App server (`f` server)

## Setting up DB server (`m` server)

## Resolving issues
