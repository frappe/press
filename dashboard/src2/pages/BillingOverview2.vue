<template>
	<div class="p-5">
		<div class="grid grid-cols-3 gap-5">
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4">
					<h2 class="text-lg font-medium text-gray-900">Billing Overview</h2>
				</div>
				<div>
					<div
						v-for="d in billingOverview"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
					</div>
				</div>
			</div>
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4">
					<h2 class="text-lg font-medium text-gray-900">Billing Details</h2>
				</div>
				<div>
					<div
						v-for="d in billingDetails"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
					</div>
				</div>
			</div>
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4">
					<h2 class="text-lg font-medium text-gray-900">Card Details</h2>
				</div>
				<div>
					<div
						v-for="d in cardDetails"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'BillingOverview2',
	computed: {
		billingOverview() {
			return [
				{
					label: 'Current Billing Amount',
					value: this.upcomingInvoice
						? this.upcomingInvoice.formatted.total
						: '0.00'
				},
				{
					label: 'Unpaid Amount',
					value:
						(this.$team.doc.currency == 'INR' ? '₹' : '$') +
						' ' +
						Math.ceil(this.$resources.unpaidAmountDue.data)
				},
				{
					label: 'Account Balance',
					value: this.availableCredits
				},
				{
					label: 'Payment Mode',
					value: this.$team.doc.payment_mode || 'Not set'
				}
			];
		},
		billingDetails() {
			return [
				{
					label: 'Billing Name',
					value: this.$team.doc.billing_name
				},
				{
					label: 'Address',
					value:
						this.$team.doc.billing_details.address_line1 +
						', ' +
						this.$team.doc.billing_details.address_line2
				},
				{
					label: 'Country',
					value: this.$team.doc.billing_details.country
				},
				{
					label: 'Pincode',
					value: this.$team.doc.billing_details.pincode
				},
				{
					label: 'GSTIN',
					value: this.$team.doc.billing_details.gstin
				},
				{
					label: 'State',
					value: this.$team.doc.billing_details.state
				}
			];
		},
		cardDetails() {
			console.log(this.$team.doc.card_details);
			return [
				{
					label: 'Card Number',
					value: '****' + ' ' + this.$team.doc.payment_method.last_4
				},
				{
					label: 'Card Expiry',
					value:
						this.$team.doc.payment_method.expiry_month +
						'/' +
						this.$team.doc.payment_method.expiry_year
				},
				{
					label: 'Card Brand',
					value: this.$team.doc.payment_method.brand
				},
				{
					label: 'Card Holder Name',
					value: this.$team.doc.payment_method.name_on_card
				}
			];
		},
		minimumAmount() {
			const unpaidAmount = this.$resources.unpaidAmountDue.data;
			const minimumDefault = this.$team.doc.currency == 'INR' ? 800 : 10;

			return Math.ceil(
				unpaidAmount && unpaidAmount > minimumDefault
					? unpaidAmount
					: minimumDefault
			);
		},
		upcomingInvoice() {
			return this.$resources.upcomingInvoice.data?.upcoming_invoice;
		},
		availableCredits() {
			if (this.$team.doc.payment_mode === 'Partner Credits') {
				return this.$resources.availablePartnerCredits.data;
			}

			return this.$resources.upcomingInvoice.data?.available_credits;
		},
		billingDetailsSummary() {
			const billingDetails = this.$team.doc.billing_details;
			if (!billingDetails) {
				return '';
			}

			const {
				billing_name,
				address_line1,
				country,
				city,
				state,
				pincode,
				gstin
			} = billingDetails;

			return [billing_name, address_line1, city, state, country, pincode, gstin]
				.filter(Boolean)
				.join(', ');
		}
	},
	resources: {
		upcomingInvoice: { url: 'press.api.billing.upcoming_invoice', auto: true },
		availablePartnerCredits() {
			return {
				url: 'press.api.billing.get_partner_credits',
				auto: this.$team.doc.payment_mode === 'Partner Credits'
			};
		},
		unpaidAmountDue() {
			return {
				url: 'press.api.billing.total_unpaid_amount',
				auto: true
			};
		}
	}
};
</script>
