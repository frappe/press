---
title: "Guide: Local Development Enviroment Setup"
---

# Local Development Environment Setup

This guide shows you how to setup your development machine for Frappe Cloud development. By the end of this guide, you will have a replica of the FC production environment.

## Introduction

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

## Creating DNS records in AWS Route53

## Press Frappe App

## Press Settings

### Let's Encrypt

### Docker

## Setting up Proxy server (`n` server)

## Setting up App server (`f` server)

## Setting up DB server (`m` server)

## Resolving issues
