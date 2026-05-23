<template>
	<div class="flex h-full flex-col">
		<Header :sticky="true">
			<Breadcrumbs
				:items="[{ label: object.list.title, route: object.list.route }]"
			/>
		</Header>
		<div class="p-5 pb-0">
			<AlertAddPaymentMode
				class="mb-5"
				v-if="$team?.doc && !$team.doc.payment_mode && !$team.doc.parent_team"
			/>
			<AlertCardExpired
				class="mb-5"
				v-if="$team?.doc && isCardExpired && $team.doc?.payment_mode == 'Card'"
			/>
			<AlertAddressDetails
				class="mb-5"
				v-if="
					$team?.doc &&
					!$team.doc?.billing_details?.name &&
					$team.doc.payment_mode
				"
			/>
			<CustomAlerts ctx_type="List Page" />
			<AlertMandateInfo
				class="mb-5"
				v-if="
					$team?.doc &&
					isMandateNotSet &&
					$team.doc.currency === 'DZD' &&
					$team.doc.payment_mode == 'Card'
				"
			/>
			<AlertUnpaidInvoices
				class="mb-5"
				v-if="
					hasUnpaidInvoices > 0 && $team.doc.payment_mode == 'Prepaid Credits'
				"
				:amount="hasUnpaidInvoices"
			/>
			<AlertCardPaymentFailed
				class="mb-5"
				v-if="
					$team?.doc &&
					cardPaymentFailure &&
					$team.doc.payment_mode == 'Card' &&
					isAfterFirstWeek &&
					!isCardExpired &&
					!isMandateNotSet
				"
				:errorMessage="cardPaymentFailure.stripe_payment_error"
				:stripeUrl="cardPaymentFailure.stripe_invoice_url"
			/>
			<AlertBudgetThreshold
				class="mb-5"
				v-if="displayBudgetAlert > 0"
				:amount="displayBudgetAlert"
				:currency="'د.ج'"
			/>
			<ObjectList :options="listOptions" />
		</div>
	</div>
</template>

<script>
import { Breadcrumbs, Button, Dropdown, TextInput } from 'frappe-ui'
import { defineAsyncComponent } from 'vue'
import Header from '../components/Header.vue'
import ObjectList from '../components/ObjectList.vue'
import { getObject } from '../objects'
import dayjs from '../utils/dayjs'

export default {
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		Button,
		Dropdown,
		TextInput,
		AlertAddPaymentMode: defineAsyncComponent(
			() => import('../components/AlertAddPaymentMode.vue'),
		),
		AlertCardExpired: defineAsyncComponent(
			() => import('../components/AlertCardExpired.vue'),
		),
		AlertAddressDetails: defineAsyncComponent(
			() => import('../components/AlertAddressDetails.vue'),
		),
		AlertMandateInfo: defineAsyncComponent(
			() => import('../components/AlertMandateInfo.vue'),
		),
		AlertUnpaidInvoices: defineAsyncComponent(
			() => import('../components/AlertUnpaidInvoices.vue'),
		),
		AlertCardPaymentFailed: defineAsyncComponent(
			() => import('../components/AlertCardPaymentFailed.vue'),
		),
		AlertBudgetThreshold: defineAsyncComponent(
			() => import('../components/AlertBudgetThreshold.vue'),
		),
		CustomAlerts: defineAsyncComponent(
			() => import('../components/CustomAlerts.vue'),
		),
	},
	props: {
		objectType: {
			type: String,
			required: true,
		},
	},
	methods: {
		getRoute(row) {
			return {
				name: `${this.object.doctype} Detail`,
				params: {
					name: row.name,
				},
			}
		},
	},
	computed: {
		object() {
			return getObject(this.objectType)
		},
		listOptions() {
			return {
				...this.object.list,
				doctype: this.object.doctype,
				route: this.object.detail ? this.getRoute : null,
			}
		},
		isCardExpired() {
			if (this.$team.doc.payment_method?.expiry_year < dayjs().year()) {
				return true
			} else if (
				this.$team.doc.payment_method?.expiry_year == dayjs().year() &&
				this.$team.doc.payment_method?.expiry_month < dayjs().month() + 1
			) {
				return true
			} else {
				return false
			}
		},
		isMandateNotSet() {
			return !this.$team.doc?.payment_method?.stripe_mandate_id
		},
		hasUnpaidInvoices() {
			return this.$resources.getAmountDue.data
		},
		isAfterFirstWeek() {
			return dayjs().date() > 6
		},
		cardPaymentFailure() {
			const invoices = this.$resources.getUnpaidInvoices.data
			if (!invoices) return null
			return (
				invoices.find((inv) => {
					if (!inv.stripe_payment_failed || !inv.stripe_invoice_url)
						return false
					const error = (inv.stripe_payment_error || '').toLowerCase()
					return (
						error.includes('insufficient fund') ||
						error.includes('mandate amount')
					)
				}) || null
			)
		},
		displayBudgetAlert() {
			if (
				!this.$team.doc.receive_budget_alerts ||
				!this.$team.doc.monthly_alert_threshold ||
				this.$team.doc.monthly_alert_threshold <= 0
			) {
				return 0
			}

			let difference =
				this.$resources.getCurrentBillingAmount.data -
				this.$team.doc.monthly_alert_threshold

			return difference > 0 ? difference.toFixed(2) : 0
		},
	},
	resources: {
		getAmountDue() {
			return {
				url: 'press.api.billing.total_unpaid_amount',
				auto: true,
			}
		},
		getUnpaidInvoices() {
			return {
				url: 'press.api.client.get_list',
				params: {
					doctype: 'Invoice',
					fields: [
						'name',
						'stripe_invoice_url',
						'stripe_payment_failed',
						'stripe_payment_error',
					],
					filters: { status: 'Unpaid', type: 'Subscription' },
					order_by: 'creation desc',
					limit: 1,
				},
				auto: this.$team?.doc?.payment_mode === 'Card' && this.isAfterFirstWeek,
			}
		},
		getCurrentBillingAmount() {
			return {
				url: 'press.api.billing.get_current_billing_amount',
				auto: true,
				cache: 'Current Billing Amount',
			}
		},
	},
}
</script>
