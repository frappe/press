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
			<p class="mt-2 text-base text-gray-600">
				{{ paymentModeDescription }}
			</p>
			<ErrorMessage
				class="mt-2"
				:message="$resources.changePaymentMode.error"
			/>
		</template>
	</Dialog>
</template>
<script>
import { DashboardError } from '../../utils/error';

export default {
	name: 'ChangePaymentModeDialog',
	props: ['modelValue'],
	inject: ['team'],
	emits: ['update:modelValue'],
	data() {
		return {
			paymentMode: this.team?.data?.payment_mode
		};
	},
	watch: {
		show(value) {
			if (!value) {
				this.paymentMode = this.team?.data?.payment_mode;
			}
		}
	},
	resources: {
		changePaymentMode() {
			return {
				url: 'press.saas.api.billing.change_payment_mode',
				params: {
					mode: this.paymentMode
				},
				onSuccess(data) {
					this.$emit('update:modelValue', false);
					this.$resources.changePaymentMode.reset();
					this.team.reload();
				},
				validate() {
					if (
						this.paymentMode == 'Card' &&
						!this.team?.data?.default_payment_method
					) {
						this.$emit('update:modelValue', false);
					}

					if (
						this.paymentMode == 'Prepaid Credits' &&
						this.team?.data?.balance === 0
					) {
						this.$emit('update:modelValue', false);
						throw new DashboardError(
							'Please add prepaid credits to your account first'
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
				'Prepaid Credits': `You will be charged from your account balance for monthly subscription`
			}[this.paymentMode];
		},
		paymentModeOptions() {
			return ['Card', 'Prepaid Credits'];
		}
	}
};
</script>
