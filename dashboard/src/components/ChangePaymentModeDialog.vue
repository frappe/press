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

			<FormControl
				v-if="paymentMode == 'Paid By Partner'"
				label="Select Frappe Partner"
				type="select"
				:options="partners"
				v-model="selectedPartner"
			/>
			<ErrorMessage
				class="mt-2"
				:message="$resources.changePaymentMode.error"
			/>
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
			selectedPartner: null,
			partners: []
		};
	},
	watch: {
		show(value) {
			if (!value) {
				this.paymentMode = this.$account.team.payment_mode;
			}
		}
	},
	onMounted() {
		this.$resources.getPartners();
	},
	resources: {
		changePaymentMode() {
			return {
				url: 'press.api.billing.change_payment_mode',
				params: {
					mode: this.paymentMode,
					partner: this.selectedPartner
				},
				onSuccess(res) {
					if (res == 'ok') {
						this.$notify({
							title: 'Email Sent to Partner',
							icon: 'check',
							color: 'green'
						});
					}
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
		getPartners() {
			return {
				url: 'press.api.account.get_frappe_partners',
				auto: true,
				onSuccess(data) {
					this.partners = data.map(d => {
						return {
							label: d.billing_name,
							value: d.name
						};
					});
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
		}
	}
};
</script>
