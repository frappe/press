<template>
	<div>
		<div class="flex">
			<GreenCheckIcon class="w-5 h-5" v-if="done" />
			<div v-else class="bg-white rounded-full">
				<FeatherIcon
					name="credit-card"
					class="w-5 h-5 text-current text-gray-700"
				/>
			</div>
			<div class="ml-2 text-lg font-medium">
				Add billing information
			</div>
		</div>
		<div class="relative pb-6 pl-7">
			<div class="mt-1 text-sm text-gray-600">
				{{ description }}
			</div>
			<Button v-if="active && !done" class="mt-2" @click="showDialog = true">
				Add billing information
			</Button>
			<div
				style="width: 1px; height: 95%"
				class="absolute top-0 left-2.5 border-r border-gray-300"
			></div>
		</div>

		<Dialog title="Add billing information" v-model="showDialog">
			<div v-if="!$account.team.billing_address">
				<div class="text-base font-medium">Address Details</div>
				<AddressForm ref="address-form" v-model="address" />
				<ErrorMessage
					class="mt-2"
					:error="$resources.updateBillingInformation.error"
				/>
				<Button
					class="mt-4"
					type="primary"
					@click="updateAddress"
					:loading="$resources.updateBillingInformation.loading"
				>
					Submit
				</Button>
			</div>

			<div class="space-y-4" v-if="$account.team.billing_address">
				<div>
					<Input
						label="Select payment mode"
						type="select"
						:options="['', 'Card', 'Prepaid Credits']"
						v-model="paymentMode"
					/>
					<p class="mt-2 text-base text-gray-600">
						{{ paymentModeDescription }}
					</p>
				</div>
				<Input
					v-if="
						$account.team.erpnext_partner && paymentMode == 'Prepaid Credits'
					"
					label="Buy Credits from"
					type="select"
					:options="['Card Payment', 'Transfer from ERPNext.com']"
					v-model="buyCreditsFrom"
				/>
				<BuyPrepaidCredits
					v-if="
						paymentMode == 'Prepaid Credits' &&
							buyCreditsFrom == 'Card Payment' &&
							!$resources.prepaidCredits.loading
					"
					:minimumAmount="minCreditsToBuy"
					@success="onPrepaidCredits"
					@cancel="paymentMode = null"
				/>
				<TransferCredits
					v-if="
						paymentMode == 'Prepaid Credits' &&
							buyCreditsFrom == 'Transfer from ERPNext.com'
					"
					:minimumAmount="minCreditsToBuy"
					@success="onSuccess"
					@cancel="paymentMode = null"
				/>
				<StripeCard
					:withoutAddress="true"
					v-if="paymentMode === 'Card'"
					@complete="onSuccess"
				/>
				<Loading
					text="Updating account balance..."
					v-if="$resources.prepaidCredits.loading"
				/>
				<Loading
					text="Updating payment information..."
					v-if="$resources.changePaymentMode.loading"
				/>
			</div>
		</Dialog>
	</div>
</template>
<script>
import AddressForm from '../components/AddressForm.vue';
import StripeCard from '../components/StripeCard.vue';
import BuyPrepaidCredits from '../components/BuyPrepaidCredits.vue';
import TransferCredits from '../components/TransferCredits.vue';

export default {
	name: 'OnboardingStepSetupPayment',
	props: ['active', 'done'],
	components: {
		AddressForm,
		StripeCard,
		BuyPrepaidCredits,
		TransferCredits
	},
	data() {
		return {
			showDialog: false,
			paymentMode: null,
			buyCreditsFrom: this.$account.team.erpnext_partner
				? null
				: 'Card Payment',
			minCreditsToBuy: this.$account.team.currency == 'INR' ? 750 : 10,
			address: {}
		};
	},
	resources: {
		updateBillingInformation() {
			return {
				method: 'press.api.account.update_billing_information',
				params: {
					billing_details: this.address
				},
				onSuccess() {
					this.$account.fetchAccount();
				}
			};
		},
		changePaymentMode() {
			return {
				method: 'press.api.billing.change_payment_mode',
				params: {
					mode: this.paymentMode
				},
				onSuccess() {
					this.$account.fetchAccount();
				}
			};
		},
		prepaidCredits() {
			return {
				method: 'press.api.billing.prepaid_credits_via_onboarding',
				onSuccess() {
					this.showDialog = false;
					this.$account.fetchAccount();
				}
			};
		}
	},
	methods: {
		onSuccess() {
			this.showDialog = false;
			this.$resources.changePaymentMode.submit();
		},
		onPrepaidCredits() {
			this.$resources.prepaidCredits.submit();
		},
		async updateAddress() {
			let errorMessage = await this.$refs['address-form'].validateValues();
			if (errorMessage) {
				this.$resources.updateBillingInformation.setError(errorMessage);
			} else {
				this.$resources.updateBillingInformation.submit();
			}
		}
	},
	computed: {
		description() {
			if (this.$account.team.via_erpnext) {
				return 'Setup your payment method for monthly billing. After that, select a plan for your ERPNext site and you are good to go.';
			}
			return 'Setup your payment method for your monthly billing. Get $25 free credits if you add your card.';
		},
		paymentModeDescription() {
			if (this.paymentMode == 'Card') {
				return 'Your card will be charged at the end of every month';
			}
			if (this.paymentMode == 'Prepaid Credits') {
				return 'You will be charged from your account balance at the end of every month';
			}
		}
	}
};
</script>
