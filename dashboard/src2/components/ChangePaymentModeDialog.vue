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
		<template #body-content>
			<FormControl
				label="Select Payment Mode"
				type="select"
				:options="paymentModeOptions"
				v-model="paymentMode"
			/>
			<p class="mb-5 mt-2 text-base text-gray-600">
				{{ paymentModeDescription }}
			</p>
			<ErrorMessage
				class="mt-2"
				:message="$resources.changePaymentMode.error"
			/>
		</template>
	</Dialog>
	<NewBillingInformationDialog
		v-model="showBillingInformationDialog"
		v-if="showBillingInformationDialog"
	/>
	<BuyPrepaidCreditsDialog
		v-if="showPrepaidCreditsDialog"
		v-model="showPrepaidCreditsDialog"
		:minimumAmount="$team.doc.currency == 'INR' ? 800 : 10"
		@success="
			() => {
				$resources.upcomingInvoice.reload();
				showPrepaidCreditsDialog = false;
			}
		"
	/>
</template>
<script>
import { defineAsyncComponent, h } from 'vue';
import { DashboardError } from '../utils/error';
import NewBillingInformationDialog from './billing/BillingInformationDialog.vue';
import { renderDialog } from '../utils/components';

export default {
	name: 'ChangePaymentModeDialog',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: {
		NewBillingInformationDialog,
		BuyPrepaidCreditsDialog: defineAsyncComponent(() =>
			import('../components/BuyPrepaidCreditsDialog.vue')
		),
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('@/components/PrepaidCreditsDialog.vue')
		)
	},
	data() {
		return {
			showBillingInformationDialog: false,
			showPrepaidCreditsDialog: false,
			paymentMode: this.$team.doc.payment_mode
		};
	},
	watch: {
		show(value) {
			if (!value) {
				this.paymentMode = this.$team.doc.payment_mode;
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
				onSuccess(data) {
					if (data && data == 'Unpaid Invoices') {
						const finalizeInvoicesDialog = defineAsyncComponent(() =>
							import('./billing/FinalizeInvoicesDialog.vue')
						);
						renderDialog(h(finalizeInvoicesDialog));
					} else {
						this.$emit('update:modelValue', false);
						this.$resources.changePaymentMode.reset();
						this.$team.reload();
					}
				},
				validate() {
					if (
						this.paymentMode == 'Card' &&
						!this.$team.doc.default_payment_method
					) {
						this.$emit('update:modelValue', false);
						this.showBillingInformationDialog = true;
					}

					if (
						this.paymentMode == 'Prepaid Credits' &&
						this.$team.doc.balance === 0
					) {
						this.$emit('update:modelValue', false);
						this.showPrepaidCreditsDialog = true;
					}

					if (
						this.paymentMode == 'Paid By Partner' &&
						!this.$team.doc.partner_email
					) {
						throw new DashboardError(
							'Please add a partner first from Partner section'
						);
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
			if (this.$team.doc.erpnext_partner) {
				return ['Card', 'Prepaid Credits'];
			}
			return ['Card', 'Prepaid Credits', 'Paid By Partner'];
		}
	}
};
</script>
