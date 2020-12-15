---
title: Plans - Billing
---

# Plans

Plans mean that you will pay a fixed monthly price for all your sites. These
plans are defined based on a mix of CPU, Database and Disk Usages.

If CPU Usages exceed, the site will start responding to all further requests
with `HTTP 429` response until the cycle recycles. In case of Database and Disk
usage violations, sites are suspended until the site's Plan is upgraded.

## Metrics

There are three metrics we use for the current plans at Frappe Cloud. Here,
we'll go over how each are calculated.

### CPU Usage

Only calculated for the CPU time used by web requests. Background Job and
Scheduled Jobs' CPU Time is excluded from this. This usage counter on your
site's dashboard resets daily.

### Database Usage

Only the real database space usage is used for this. Usage is calculated using
your site's information schema table. This value may differ greatly from the
size of your compressed or decompressed backup files. This usage is calculated
and updated daily on your site's dashboard.

### Disk Usage

This is calculated using the sum of your site's private and public files. We
don't include your local backups in this. This usage is calculated and updated
daily on your site's dashboard.

## Units

We will try to explain the units for calculating the limits and usages of your
sites here.

### CPU Units

Usage is calculated in seconds and managed by Frappe's [Rate
Limiting](https://frappeframework.com/docs/user/en/rate-limiting) module.

### Storage Units

Frappe Cloud Storage is calculated with base 1024 instead of 1000. However, to
avoid confusion we've used GB instead of GiB on the pricing page and the
dashboard. This means you get more space than prescribed in real terms.

When purchasing disk drives, 1 GB is often defined as 1,000,000,000 bytes.
However, when viewed by an operating system, the capacity displayed is often
less than this. GiB (Gibibytes) is a standard unit used in the field of data
processing and transmission and is defined as base 1024 rather than base 1000.

<br>

> Refer to the Frappe Cloud [Pricing Page](/pricing) for the latest information
> about all plans.
