---
title: "Guide: Local Development Enviroment Setup"
---

# Local Development Environment Setup

This guide shows you how to setup your development machine for Frappe Cloud development. By the end of this guide, you will have a replica of the FC production environment.

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

## Press Frappe App

On your computer, `get-app` press using this [GitHub URL](https://github.com/frappe/press). Now, create a new site and install `press` on this site.

Run the site and login as admin.

## Press Settings

### Let's Encrypt

### Docker

## Setting up Proxy server (`n` server)

## Setting up App server (`f` server)

## Setting up DB server (`m` server)

## Resolving issues
