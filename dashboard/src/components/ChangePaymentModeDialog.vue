<template>
	<Dialog
		title="Change Payment Mode"
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
	>
		<Input
			label="Select Payment Mode"
			type="select"
			:options="paymentModeOptions"
			v-model="paymentMode"
		/>
		<p class="mt-2 text-base text-gray-600">
			{{ paymentModeDescription }}
		</p>
		<ErrorMessage class="mt-2" :error="$resources.changePaymentMode.error" />
		<template #actions>
			<Button
				type="primary"
				class="mt-2"
				@click="$resources.changePaymentMode.submit()"
				:loading="$resources.changePaymentMode.loading"
			>
				Change
			</Button>
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'ChangePaymentModeDialog',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			paymentMode: this.$account.team.payment_mode || 'Card'
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
				method: 'press.api.billing.change_payment_mode',
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
						return 'Please add a card first from Payment methods section';
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
				'Partner Credits': `You will be charged from your partner credits on frappe.io`
			}[this.paymentMode];
		},
		paymentModeOptions() {
			if (this.$account.team.erpnext_partner) {
				return ['Card', 'Prepaid Credits', 'Partner Credits'];
			}
			return ['Card', 'Prepaid Credits'];
		}
	}
};
</script>
