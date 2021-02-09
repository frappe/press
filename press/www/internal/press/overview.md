---
title: Press
---

# Press

Steps to setup your own production/development press installation.

### Basic

- **Domain** - Domain to use for Frappe Cloud sites and servers. You should have access to the DNS settings of this domain (See DNS section).

### DNS

This is necessary for obtaining Wildcard TLS certificates.

Currently only supported provider is AWS Route 53, uses [Route 53 plugin for Certbot](https://certbot-dns-route53.readthedocs.io/en/stable/).

### Let's Encrypt

- **Certbot Directory**: 

  By default Certbot uses `/etc/letsencrypt`, `/var/log/letsencrypt` and `/var/lib/letsencrypt` directories. Writing to these directories requires root access, to avoid this, we use `--logs-dir`, `--work-dir` and `--config-dir` flags to run certbot commands without root privileges.


- **Webroot Directory**:

  This directory is used for acquiring TLS certificates for custom domains using [Webroot plugin for Certbot](https://certbot.eff.org/docs/using.html#webroot).

  Skip this if you don't plan to use custom domains.

> Note: Both these directories should be writable by the frappe user. If the directories don't exist then they'll be created.

- **Staging CA**: Check this to use [Let's Encrypt Staging Environment](https://letsencrypt.org/docs/staging-environment/) when experimenting with TLS certificates.

- **EFF Registration Email**: EFF will send expiry, renewal and other updates on this email.

After setting these, click **Obtain TLS Certificate** (Requires **Basic** > **Domain**, and **DNS** section to be setup).

### GitHub

1. Go To **Press Settings** > **GitHub** 
1. Click on **Create GitHub App**
1. Name your app and click **Create GitHub App for ...**

  ![GitHub App Create](/assets/press/images/internal/press/github/github-app-create.png)
1. You'll be redirected to Press Settings.

  ![GitHub App Created](/assets/press/images/internal/press/github/github-app-created.png)


1. Create a GitHub Personal Access Token and add it in GitHub Access Token field.

  This is nedded for custom apps that are added without using the app creation flow (Dashboard > New App... ).
  As these are subject stricter [rate limits](https://docs.github.com/en/free-pro-team@latest/rest/overview/resources-in-the-rest-api#rate-limiting) (5000 requests/hour vs 60 requests/hour).

### Docker

**Docker Registry**: Built docker images are pushed here (this can be self hosted service or a managed container registry e.g. Docker Hub, DigitalOcean Container Registry, Amazon ECR etc.).

**Clone Directory**: Custom apps are cloned and kept in this directory to avoid repeated cloning. Directory Structure looks like this
  
```bash
.
├── frappe/
│   ├── release-1/
│   └── release-2/
└── erpnext/
    ├── release-1/
    └── release-2/
```
**Build Directory**: Directory for docker build contexts. Directory Structure looks like this

```bash
.
├── bench-1/
│   ├── build-1/
│   └── build-2/
└── bench-2/
    ├── build-1/
    └── build-2/
```
**Code Server**: (Not required) Visual Studio Codeserver instance for read only access to cloned apps for manual review. Requires a password to access.