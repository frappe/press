---
title: Billing Cycle - Billing
---

# Billing Cycle

Overview of Frappe Cloud's Billing Process

Frappe Cloud billing cycles are monthly. Each site is microbilled on a daily
basis. When you select a plan, the monthly amount is divided by the number of
days in the current calendar month. You are charged based on the number of days
your site remains active at the end of the month.

[![Billing Dashboard](/assets/press/images/docs/account-billing.png)](/assets/press/images/docs/account-billing.png)

You can access and update your billing information from
[/dashboard/account/billing](/dashboard/account/billing). The dashboard also
shows information regarding the current usage from all your active sites.

> We finalize invoices on **the last day of each month at 6 PM IST**. Sites
created after this point will be a part of next month's billing cycle.

## Use Cases

Here's an attempt to explain the process by considering a few use cases:

### Single plan throughout the calendar month

When you select the `$100` plan for your site `raftel.frappe.cloud`, every day
your site remains active, `$3.33` is accrued to your monthly usage in case of a
30 day month. For the month of April, the estimate would look something like

| - | Base Plan | No. of Days | Rate | Total |
| --- | ----- | ------------ | -------------- | --------------- |
| | $100 | 30 | $3.33/day | $99.9 |
| | | | | **$99.9** |

This rate may go to `$3.23` in case of a 31 day month or `$3.57` in case of a 28
day month. This means that you are charged no more than `$100` for hosting your
site each month. For February 2024 (leap year), this would look something like

| - | Base Plan | No. of Days | Rate | Total |
| --- | ----- | ------------ | -------------- | --------------- |
| | $100 | 29 | $3.45/day | $100.05 |
| | | | | **$100.05** |

### Multiple plans throughout the calendar month

Another instance of hosting a site `laugh-tale.frappe.cloud` on `$200` plan.
After 15 days, you need more CPU time and decide to upgrade to plan `$500`. For
a 31 day month, you get charged `$354.84` in total. Here's the break up.

| - | Base Plan | No. of Days | Rate | Total |
| --- | ----- | ------------ | -------------- | --------------- |
| | $200 | 15 | $6.45/day | $96.77 |
| | $500 | 16 | $16.13/day | $258.07 |
| | | | | **$354.84** |

### Site dropped in the middle of the month

If you drop your site `arabasta.frappe.cloud` 4 days into the month, you will be
charged for those 4 days.

| - | Base Plan | No. of Days | Rate | Total |
| --- | ----- | ------------ | -------------- | --------------- |
| | $200 | 4 | $6.45/day | $25.8 |
| | | | | **$25.8** |

> Even if you might drop all your sites mid-way, you will receive the invoice at
> the end of the month.
