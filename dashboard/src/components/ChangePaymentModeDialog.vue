<template>
	<Dialog
		:options="{
			title: 'Change Payment Mode',
			actions: [
				{
					label: 'Change',
					variant: 'solid',
					loading: $resources.changePaymentMode.loading,
					onClick: () => $resources.changePaymentMode.submit()
				}
			]
		}"
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
	>
		<template v-slot:body-content>
			<FormControl
				label="Select Payment Mode"
				type="select"
				:options="paymentModeOptions"
				v-model="paymentMode"
			/>
			<p class="mt-2 text-base text-gray-600 mb-5">
				{{ paymentModeDescription }}
			</p>
			<ErrorMessage
				class="mt-2"
				:message="$resources.changePaymentMode.error"
			/>
		</template>
	</Dialog>
	<BillingInformationDialog
		v-model="showBillingInformationDialog"
		v-if="showBillingInformationDialog"
	/>
	<PrepaidCreditsDialog
		v-if="showPrepaidCreditsDialog"
		v-model:show="showPrepaidCreditsDialog"
		:minimumAmount="$account.team.currency == 'INR' ? 800 : 10"
		@success="
			() => {
				$resources.upcomingInvoice.reload();
				showPrepaidCreditsDialog = false;
			}
		"
	/>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'ChangePaymentModeDialog',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: {
		BillingInformationDialog: defineAsyncComponent(() =>
			import('./BillingInformationDialog.vue')
		),
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('@/components/PrepaidCreditsDialog.vue')
		)
	},
	data() {
		return {
			showBillingInformationDialog: false,
			showPrepaidCreditsDialog: false,
			paymentMode: this.$account.team.payment_mode
		};
	},
	watch: {
		show(value) {
			if (!value) {
				this.paymentMode = this.$account.team.payment_mode;
			}
		}
	},
	resources: {
		changePaymentMode() {
			return {
				url: 'press.api.billing.change_payment_mode',
				params: {
					mode: this.paymentMode
				},
				onSuccess() {
					this.$emit('update:modelValue', false);
					this.$resources.changePaymentMode.reset();
				},
				validate() {
					if (
						this.paymentMode == 'Card' &&
						!this.$account.team.default_payment_method
					) {
						this.$emit('update:modelValue', false);
						this.showBillingInformationDialog = true;
					}

					if (
						this.paymentMode == 'Prepaid Credits' &&
						this.$account.balance === 0
					) {
						this.$emit('update:modelValue', false);
						this.showPrepaidCreditsDialog = true;
					}

					if (
						this.paymentMode == 'Paid By Partner' &&
						!this.$account.team.partner_email
					) {
						return 'Please add a partner first from Partner section';
					}
				}
			};
		}
	},
	computed: {
		paymentModeDescription() {
			return {
				Card: `Your card will be charged for monthly subscription`,
				'Prepaid Credits': `You will be charged from your account balance for monthly subscription`,
				'Paid By Partner': `Your partner will be charged for monthly subscription`
			}[this.paymentMode];
		},
		paymentModeOptions() {
			if (this.$account.team.erpnext_partner) {
				return ['Card', 'Prepaid Credits'];
			}
			return ['Card', 'Prepaid Credits', 'Paid By Partner'];
		}
	}
};
</script>
