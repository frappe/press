<template>
	<div>
		<div class="mb-10 text-gray-800" v-if="state === 'RequestStarted'">
			Fetching billing information...
		</div>
		<section v-if="upcomingInvoice" class="mb-10">
			<h2 class="text-lg font-medium">
				Upcoming Invoice
			</h2>
			<p class="text-gray-600">
				This is the amount so far based on the usage of your sites
			</p>
			<div
				class="w-full py-2 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div class="grid grid-cols-3 px-6 py-3 text-sm">
					<div class="font-medium text-gray-700">Available Credits:</div>
					<div class="col-span-2 font-medium">
						<div>
							{{ availableCredits }}
						</div>
						<div v-if="$store.account.team.erpnext_partner" class="mt-2">
							<a
								href
								class="text-blue-500 cursor-pointer"
								@click.prevent="
									fetchAvailablePartnerCredits();
									showTransferCreditsDialog = true;
								"
							>
								Transfer Credits from ERPNext.com
							</a>
						</div>
						<Dialog
							v-model="showTransferCreditsDialog"
							title="Transfer Credits from ERPNext.com"
						>
							<p v-if="availablePartnerCredits">
								Available credits: {{ availablePartnerCredits.formatted }}
							</p>
							<label class="block" v-if="availablePartnerCredits">
								<span class="text-gray-800 sr-only">Amount to Transfer</span>
								<input
									class="block w-full mt-2 shadow form-input"
									v-model.number="creditsToTransfer"
									name="amount"
									autocomplete="off"
									type="number"
									min="1"
									:max="availablePartnerCredits.value"
								/>
							</label>
							<ErrorMessage class="mt-2" v-if="errorMessage">
								{{ errorMessage }}
							</ErrorMessage>
							<template slot="actions">
								<Button @click="showTransferCreditsDialog = false">
									Cancel
								</Button>
								<Button
									class="ml-2"
									type="primary"
									@click="transferPartnerCredits"
									:disabled="
										creditsToTransfer <= 0 || state === 'RequestStarted'
									"
								>
									Transfer
								</Button>
							</template>
						</Dialog>
					</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-sm border-t">
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
				History of your invoice payments
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
		<section v-if="paymentMethods && paymentMethods.length === 0">
			<h2 class="text-lg font-medium">Set up Payment Method</h2>
			<p class="text-gray-600">
				Add your card details to start your subscription
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div class="px-6 py-4">
					<Button
						type="primary"
						@click="state = 'ShowStripeCard'"
						v-if="state != 'ShowStripeCard'"
					>
						Set up Payment Method
					</Button>
					<StripeCard v-if="state === 'ShowStripeCard'" @complete="onCardAdd" />
				</div>
			</div>
		</section>
		<section v-if="paymentMethods && paymentMethods.length > 0">
			<h2 class="text-lg font-medium">Payment Methods</h2>
			<p class="text-gray-600">
				Cards you have added for automatic billing
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div
					class="grid items-center grid-cols-5 px-6 py-4 hover:bg-gray-50"
					v-for="paymentMethod in paymentMethods"
					:key="paymentMethod.name"
				>
					<div class="font-semibold">•••• {{ paymentMethod.last_4 }}</div>
					<div class="col-span-2">
						{{ paymentMethod.name_on_card }}
					</div>
					<div class="text-right">
						{{ paymentMethod.expiry_month }} /
						{{ paymentMethod.expiry_year }}
					</div>
					<div class="text-right">
						<Badge v-if="paymentMethod.is_default" color="blue">Default</Badge>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
import Dialog from '@/components/Dialog';

export default {
	name: 'AccountBilling',
	components: {
		StripeCard,
		Dialog
	},
	data() {
		return {
			state: null,
			errorMessage: null,
			paymentMethods: null,
			upcomingInvoice: null,
			availableCredits: null,
			pastPayments: [],
			showTransferCreditsDialog: false,
			availablePartnerCredits: null,
			creditsToTransfer: null
		};
	},
	async mounted() {
		await this.fetchUpcomingInvoice();
		await this.fetchPaymentMethods();
	},
	methods: {
		async fetchPaymentMethods() {
			this.paymentMethods = await this.$call(
				'press.api.billing.get_payment_methods'
			);
			if (this.paymentMethods.length === 0) {
				this.state = 'ShowSetup';
			}
		},
		async fetchUpcomingInvoice() {
			let {
				upcoming_invoice = null,
				past_payments = [],
				available_credits = 0
			} = (await this.$call('press.api.billing.info')) || {};
			this.upcomingInvoice = upcoming_invoice;
			this.pastPayments = past_payments;
			this.availableCredits = available_credits;
		},
		onCardAdd() {
			this.fetchPaymentMethods();
			this.$call('press.api.billing.after_card_add');
		},
		async fetchAvailablePartnerCredits() {
			this.availablePartnerCredits = await this.$call(
				'press.api.billing.get_available_partner_credits'
			);
		},
		async transferPartnerCredits() {
			await this.$call('press.api.billing.transfer_partner_credits', {
				amount: this.creditsToTransfer
			});
			this.fetchUpcomingInvoice();
			this.creditsToTransfer = null;
			this.showTransferCreditsDialog = false;
		}
	}
};
</script>
