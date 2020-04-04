<template>
	<div>
		<div class="text-gray-800" v-if="state === 'Fetching'">
			Fetching billing information..
		</div>
		<section v-if="upcomingInvoice" class="mb-10">
			<h2 class="text-lg font-medium">
				Upcoming Invoice
			</h2>
			<p class="text-gray-600">
				This is the amount so far based on the usage of your sites.
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div class="grid grid-cols-3 px-6 py-3 text-sm">
					<div class="font-medium text-gray-700">Usage Amount:</div>
					<div class="col-span-2 font-medium">{{ upcomingInvoice.amount }}</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-sm border-t">
					<div class="font-medium text-gray-700">Next Invoice Date:</div>
					<div class="col-span-2 font-medium">
						{{ upcomingInvoice.next_payment_attempt }}
					</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-sm border-t">
					<div class="font-medium text-gray-700">Bill To:</div>
					<div class="col-span-2 font-medium">
						{{ upcomingInvoice.customer_email }}
					</div>
				</div>
			</div>
		</section>
		<section v-if="pastPayments.length" class="mb-10">
			<h2 class="text-lg font-medium">Past Payments</h2>
			<p class="text-gray-600">
				Your last 3 payments
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div
					class="grid items-center grid-cols-3 px-6 py-4 hover:bg-gray-50"
					v-for="payment in pastPayments"
					:key="payment.stripe_invoice_id"
				>
					<div class="font-semibold">
						<div v-if="payment.status === 'Paid'">
							{{ payment.payment_date }}
						</div>
						<div v-else-if="payment.payment_link">
							<a
								class="inline-flex items-center justify-center text-blue-500"
								:href="payment.payment_link"
								target="_blank"
							>
								Pay Now
								<FeatherIcon name="arrow-right" class="w-4 h-4 ml-2" />
							</a>
						</div>
					</div>
					<div>{{ payment.formatted_amount }}</div>
					<div>
						<Badge :color="{ Paid: 'green', Failed: 'red' }[payment.status]">
							{{ payment.status }}
						</Badge>
					</div>
				</div>
			</div>
		</section>
		<section v-if="state.startsWith('ShowSetup')">
			<h2 class="text-lg font-medium">Setup Payment Method</h2>
			<p class="text-gray-600">
				Add your card details to start your subscription
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div class="px-6 py-4">
					<Button
						type="primary"
						@click="state = 'ShowSetup.ShowStripeCard'"
						v-if="state != 'ShowSetup.ShowStripeCard'"
					>
						Setup Payment Method
					</Button>
					<StripeCard
						v-if="state === 'ShowSetup.ShowStripeCard'"
						@complete="onCardAdd"
					/>
				</div>
			</div>
		</section>
		<section v-if="state === 'ShowPaymentMethods'">
			<h2 class="text-lg font-medium">Payment Methods</h2>
			<p class="text-gray-600">
				Cards you have added for automatic billing
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div
					class="grid items-center grid-cols-3 px-6 py-4 hover:bg-gray-50"
					v-for="paymentMethod in paymentMethods"
					:key="paymentMethod.id"
				>
					<div class="font-semibold">•••• {{ paymentMethod.card.last4 }}</div>
					<div>
						{{ paymentMethod.billing_details.name }}
					</div>
					<div>
						{{ paymentMethod.card.exp_month }} /
						{{ paymentMethod.card.exp_year }}
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
export default {
	name: 'AccountBilling',
	components: {
		StripeCard
	},
	data() {
		return {
			state: 'Idle',
			paymentMethods: null,
			upcomingInvoice: null,
			pastPayments: []
		};
	},
	mounted() {
		this.state = 'Fetching';
		this.fetchPaymentMethods();
		this.fetchUpcomingInvoice();
	},
	methods: {
		async fetchPaymentMethods() {
			this.paymentMethods = await this.$call(
				'press.api.billing.get_payment_methods'
			);
			if (this.paymentMethods.length > 0) {
				this.state = 'ShowPaymentMethods';
			} else {
				this.state = 'ShowSetup';
			}
		},
		async fetchUpcomingInvoice() {
			let { upcoming_invoice, past_payments } = await this.$call(
				'press.api.billing.get_invoices'
			);
			this.upcomingInvoice = upcoming_invoice;
			this.pastPayments = past_payments;
		},
		onCardAdd() {
			this.state = 'Idle';
			this.fetchPaymentMethods();
			this.$call('press.api.billing.after_card_add');
		}
	}
};
</script>
