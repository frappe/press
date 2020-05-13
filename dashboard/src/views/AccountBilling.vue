<template>
	<div>
		<div class="mb-10 text-gray-800" v-if="state === 'RequestStarted'">
			Fetching billing information...
		</div>
		<Section
			v-if="upcomingInvoice"
			class="mb-10"
			title="Upcoming Invoice"
			description="This is the amount so far based on the usage of your sites"
		>
			<SectionCard>
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
							<ErrorMessage
								class="mt-2"
								:error="$resources.transferPartnerCredits.error"
							/>
							<template slot="actions">
								<Button @click="showTransferCreditsDialog = false">
									Cancel
								</Button>
								<Button
									class="ml-2"
									type="primary"
									@click="$resources.transferPartnerCredits.submit()"
									:loading="$resources.transferPartnerCredits.loading"
									:disabled="creditsToTransfer <= 0"
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
			</SectionCard>
		</Section>

		<Section
			v-if="pastPayments.length"
			class="mb-10"
			title="Past Payments"
			description="History of your invoice payments"
		>
			<SectionCard>
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
			</SectionCard>
		</Section>
		<Section
			v-if="paymentMethods && paymentMethods.length === 0"
			title="Set up Payment Method"
			description="Add your card details to start your subscription"
		>
			<SectionCard>
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
			</SectionCard>
		</Section>
		<Section
			v-if="paymentMethods && paymentMethods.length > 0"
			title="Payment Methods"
			description="Cards you have added for automatic billing"
		>
			<SectionCard>
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
			</SectionCard>
		</Section>
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
	resources: {
		billingDetails: {
			method: 'press.api.billing.info',
			default: {
				upcoming_invoice: null,
				available_credits: null,
				past_payments: []
			},
			auto: true
		},
		paymentMethods: {
			method: 'press.api.billing.get_payment_methods',
			auto: true,
			onSuccess: paymentMethods => {
				if (paymentMethods.length === 0) {
					this.state = 'ShowSetup';
				}
			}
		},
		transferPartnerCredits() {
			return {
				method: 'press.api.billing.transfer_partner_credits',
				params: {
					amount: this.creditsToTransfer
				},
				onSuccess() {
					this.$resources.billingDetails.reload();
					this.creditsToTransfer = null;
					this.showTransferCreditsDialog = false;
				}
			};
		}
	},
	data() {
		return {
			state: null,
			showTransferCreditsDialog: false,
			availablePartnerCredits: null,
			creditsToTransfer: null
		};
	},
	computed: {
		upcomingInvoice() {
			return this.billingDetails.data.upcoming_invoice;
		},
		pastPayments() {
			return this.billingDetails.data.past_payments;
		},
		availableCredits() {
			return this.billingDetails.data.available_credits;
		}
	},
	methods: {
		onCardAdd() {
			this.$resources.paymentMethods.reload();
			this.$call('press.api.billing.after_card_add');
		},
		async fetchAvailablePartnerCredits() {
			this.availablePartnerCredits = await this.$call(
				'press.api.billing.get_available_partner_credits'
			);
		}
	}
};
</script>
