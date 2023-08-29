<template>
	<Dialog
		:options="{ title: 'Change Payment Mode' }"
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
	>
		<template v-slot:body-content>
			<Input
				label="Select Payment Mode"
				type="select"
				:options="paymentModeOptions"
				v-model="paymentMode"
			/>
			<p class="mt-2 text-base text-gray-600 mb-5">
				{{ paymentModeDescription }}
			</p>

			<Input
				v-if="paymentMode == 'Paid By Partner'"
				label="Select Frappe Partner"
				type="select"
				:options="frappePartners"
				v-model="frappePartner"
			/>
			<ErrorMessage
				class="mt-2"
				:message="$resources.changePaymentMode.error"
			/>
		</template>

		<template #actions>
			<Button
				appearance="primary"
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
			paymentMode: this.$account.team.payment_mode || 'Card',
			frappePartner: ''
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
		},
		partners() {
			return {
				method: 'press.api.billing.get_frappe_partners',
				onSuccess(data) {
					this.frappePartners = data;
				}
			};
		}
	},
	computed: {
		paymentModeDescription() {
			return {
				Card: `Your card will be charged for monthly subscription`,
				'Prepaid Credits': `You will be charged from your account balance for monthly subscription`,
				'Partner Credits': `You will be charged from your partner credits on frappe.io`,
				'Paid By Partner': `Your partner will be charged for monthly subscription`
			}[this.paymentMode];
		},
		paymentModeOptions() {
			if (this.$account.team.erpnext_partner) {
				return ['Card', 'Prepaid Credits', 'Partner Credits'];
			}
			return ['Card', 'Prepaid Credits', 'Paid By Partner'];
		},
		frappePartners() {
			let partners = [];
			let data = this.$resources.partners.data;
			partners = data.forEach(d => d.billing_name);
			return partners;
		}
	}
};
</script>
