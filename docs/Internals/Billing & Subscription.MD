---
route: billing-and-subscription-internal
allow_guest: 1
published: 1
---

This page describes how Subscription Management works in Frappe Cloud.

## DocTypes

These are the key doctypes that are related to subscription:

1. [Plan](/app/plan): List of plans
2. [Subscription](/app/subscription): Record of active subscriptions
3. [Usage Record](/app/usage-record): Record of usage on a date
4. [Invoice](/app/invoice): Document that collects all usage records and creates a Stripe
 invoice at the end of the month
5. [Balance Transaction](/app/balance-transaction): Document that keeps track of credits (Free Credits,
 Prepaid Credits, Transferred Credits)
6. [Site](/app/site): Site that is charged


## Example scenario:

John registers on frappecloud.com with the email john@doe.com on 5 January,
2021. A Team record will be created with the name **john@doe.com** and a Stripe
customer record will also be created and linked to this Team record.

Now, he completes the onboarding steps, which involves adding their card for
future billing. This card is added directly on Stripe. On adding a card, he also
gets a free $25 credit. A Balance Transaction of amount +$25 is created to track
this.

Now, he creates a site called **tennismart.frappe.cloud** on the $10 plan. 

- A site record of tennismart.frappe.cloud will be created.
- A subscription record saying that this site is on $10 plan will be created.

Frappe Cloud charges you based on how many active sites you have per day. So,
the per day charge of an active site is $10 / 31 = $0.32. We divide by 31 since
that is the total number of days in January.

Now, the site is active for 5 days. The total usage amount will $0.32 * 5 = $1.6.

This is how it will look in the invoice:

| Site | Plan | Days | Amount |
| ----------------------- | ---- | ---- | ------ |
| tennismart.frappe.cloud | $10 | 5 | $1.6 |

Now, John decides to upgrade the plan to $25 because he needs more CPU time for
the kind of tasks he is running on his site. The plan in the Subscription record
will be updated to $25 and now for each day his site is active $25 / 31 = $0.8
will be charged.

This is how it will look in the invoice:

| Site | Plan | Days | Amount |
| ----------------------- | ---- | ---- | ------ |
| tennismart.frappe.cloud | $10 | 5 | $1.6 |
| tennismart.frappe.cloud | $25 | 1 | $0.8 |

Now, John creates another site cafelegals.frappe.cloud on the $50 plan. After 10
days of usage, this is how his invoice will look:

| Site | Plan | Days | Amount |
| ----------------------- | ---- | ---- | ------ |
| tennismart.frappe.cloud | $10 | 5 | $1.6 |
| tennismart.frappe.cloud | $25 | 11 | $8.8 |
| cafelegals.frappe.cloud | $50 | 10 | $16.1 |

Now, John deletes the site cafelegals.frappe.cloud because he doesn't have any
use for it. Frappe Cloud will stop charging for the site. After 2 days, this is
how his invoice will look:

| Site | Plan | Days | Amount |
| -------------------------------- | ---- | ---- | ------ |
| tennismart.frappe.cloud | $10 | 5 | $1.6 |
| tennismart.frappe.cloud | $25 | 13 | $10.4 |
| cafelegals.frappe.cloud.archived | $50 | 10 | $16.1 |

If you notice, only the usage for tennismart.frappe.cloud was updated.

Now, let's fast forward to the end of the month on 31 January, 2021. This is how
his invoice will look like:

| Site | Plan | Days | Amount |
| -------------------------------- | ---- | --------- | ------ |
| tennismart.frappe.cloud | $10 | 5 | $1.6 |
| tennismart.frappe.cloud | $25 | 22 | $17.6 |
| cafelegals.frappe.cloud.archived | $50 | 10 | $16.1 |
| | | **Total** | $35.3 |

Notice that since he started using the Frappe Cloud service from 5 January, he
was only charged from that day.

Now, at 6pm IST his invoice will be finalized with the total usage amount $35.3.
But he already has a $25 credit. So, the total amount due is $35.3 - $25 =
$10.3.

| Site | Plan | Days | Amount |
| -------------------------------- | ---- | ------------------- | ------ |
| tennismart.frappe.cloud | $10 | 5 | $1.6 |
| tennismart.frappe.cloud | $25 | 22 | $17.6 |
| cafelegals.frappe.cloud.archived | $50 | 10 | $16.1 |
| | | **Total** | $35.3 |
| | | **Applied Credits** | - $25 |
| | | **Amount Due** | $10.3 |

A Stripe invoice will be created with the amount $10.3 and his card will be
charged. A new invoice will be created for the upcoming month of February.

## Scheduler Events

### [subscription.create\_usage\_records](https://github.com/frappe/press/blob/master/press/press/doctype/subscription/subscription.py#L109) (hourly_long)

This job runs hourly and creates a Usage Record for every active Subscription.
It will not create more than one record per day for one Subscription even if it
runs hourly. This is to minimize abuse of our service in the scenario where
someone creates a site in the morning and deletes in the night only to create it
in the morning again.

Now, for every Usage Record that is created, the amount is updated in the
corresponding invoice for that month. For e.g., if a Usage Record of $0.32 is
created in the month of January, the amount will updated in the January invoice.

### [invoice.finalize\_draft\_invoices](https://github.com/frappe/press/blob/master/press/press/doctype/invoice/invoice.py#L541) (Daily at 6pm IST)

This job runs every day at 6pm IST. It will go through every Draft Invoice whose
period_end date has ended (today or before) and has a total amount greater than
0. When an invoice is finalized, credits are applied first if any, and then if
the amount_due is greater than 0 a Stripe invoice is created.

After a Stripe invoice is created, Stripe will initiate the charge after one
hour of invoice creation. This means if the invoice was created at 6pm, Stripe
will charge the card at 7pm.

Stripe will send a webhook for the payment status. If the payment was
successful, the Invoice status will be changed to Paid. If the payment was
unsuccessful, the Invoice status will be changed to Unpaid. Stripe will attempt
the charge for 3 more times.
