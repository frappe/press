<template>
	<div>
		<Section
			class="mb-10"
			title="Upcoming Invoice"
			description="This is the amount so far based on the usage of your sites"
		>
			<SectionCard>
				<div
					class="px-6 py-3 text-base text-gray-800"
					v-if="$resources.billingDetails.loading"
				>
					Fetching billing information...
				</div>
				<template v-if="upcomingInvoice">
					<DescriptionList
						class="px-6 py-4"
						:items="
							[
								{
									label: 'Usage So Far',
									value: upcomingInvoice.total_amount
								},
								{
									label: 'Available Credits',
									value: availableCredits
								},
								upcomingInvoice.next_payment_attempt
									? {
											label: 'Next Invoice Date',
											value: upcomingInvoice.next_payment_attempt
									  }
									: null,
								{
									label: 'Billed To',
									value: upcomingInvoice.customer_email
								}
							].filter(Boolean)
						"
					/>
				</template>
				<div
					class="px-6 pb-4"
					v-if="!$resources.billingDetails.loading && !paymentMethodAdded"
				>
					<Button type="primary" route="/welcome">
						Add Billing Information
					</Button>
				</div>
				<div
					class="px-6 pb-2"
					v-if="upcomingInvoice && $account.team.erpnext_partner"
				>
					<Button
						@click="
							fetchAvailablePartnerCredits();
							showTransferCreditsDialog = true;
						"
					>
						Transfer Credits from ERPNext.com
					</Button>
				</div>
			</SectionCard>
		</Section>

		<Dialog
			v-model="showTransferCreditsDialog"
			title="Transfer Credits from ERPNext.com"
		>
			<Input
				v-if="availablePartnerCredits"
				:label="
					`Amount to Transfer (Credits available: ${availablePartnerCredits.formatted})`
				"
				v-model.number="creditsToTransfer"
				name="amount"
				autocomplete="off"
				type="number"
				min="1"
				:max="availablePartnerCredits.value"
			/>
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
					<div class="text-base font-semibold">
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
					<div class="text-base">{{ payment.formatted_amount }}</div>
					<div>
						<Badge :color="{ Paid: 'green', Failed: 'red' }[payment.status]">
							{{ payment.status }}
						</Badge>
					</div>
				</div>
			</SectionCard>
		</Section>
		<Section
			v-if="paymentMethods.data && paymentMethods.data.length > 0"
			title="Payment Methods"
			description="Cards you have added for automatic billing"
		>
			<SectionCard>
				<div
					class="grid items-center grid-cols-5 px-6 py-4 text-base hover:bg-gray-50"
					v-for="paymentMethod in paymentMethods.data"
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
				<div class="px-6 py-4">
					<Button type="primary" @click="showStripeCardDialog = true">
						Add Payment Method
					</Button>
					<Dialog
						title="Add Billing Information"
						v-model="showStripeCardDialog"
					>
						<StripeCard
							class="mb-1"
							v-if="showStripeCardDialog"
							@complete="onCardAdd"
						/>
					</Dialog>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
import Dialog from '@/components/Dialog';
import DescriptionList from '@/components/DescriptionList';

export default {
	name: 'AccountBilling',
	components: {
		StripeCard,
		Dialog,
		DescriptionList
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
			auto: true
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
			showStripeCardDialog: false,
			showTransferCreditsDialog: false,
			availablePartnerCredits: null,
			creditsToTransfer: null
		};
	},
	computed: {
		paymentMethodAdded() {
			return this.billingDetails.data?.payment_method;
		},
		upcomingInvoice() {
			return this.billingDetails.data?.upcoming_invoice;
		},
		pastPayments() {
			return this.billingDetails.data?.past_payments || [];
		},
		availableCredits() {
			return this.billingDetails.data?.available_credits;
		}
	},
	methods: {
		onCardAdd() {
			this.showStripeCardDialog = false;
			this.$resources.paymentMethods.reload();
		},
		async fetchAvailablePartnerCredits() {
			this.availablePartnerCredits = await this.$call(
				'press.api.billing.get_available_partner_credits'
			);
		}
	}
};
</script>
