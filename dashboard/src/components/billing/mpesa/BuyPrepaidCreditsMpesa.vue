<template>
	<div>
		<label class="block mt-4">
			<span class="text-sm leading-4 text-gray-700"> </span>
			<ErrorMessage class="mt-1" :message="paymentErrorMessage" />
		</label>

		<ErrorMessage class="mt-2" :message="errorMessage" />

		<FormControl
			type="combobox"
			:options="teams"
			size="sm"
			variant="subtle"
			placeholder="Payment Partner"
			:disabled="false"
			label="Select Payment Partner"
			:modelValue="partnerInput"
			@update:modelValue="partnerInput = $event"
			class="mb-5"
		/>

		<div class="flex gap-5 col-2">
			<FormControl
				label="M-Pesa Phone Number"
				v-model="phoneNumberInput"
				name="phone_number"
				autocomplete="off"
				class="mb-5"
				type="number"
				placeholder="e.g 123456789"
			/>

			<FormControl
				label="Tax ID"
				v-model="taxIdInput"
				name="tax_id"
				autocomplete="off"
				class="mb-5"
				type="string"
				placeholder="e.g A123456789A"
			/>
		</div>
		<!-- Show amount after tax -->
		<div v-if="showTaxInfo" class="flex col-2 gap-5">
			<FormControl
				label="Tax(%)"
				disabled
				:modelValue="taxPercentage"
				type="number"
			/>

			<FormControl
				label="Total Amount With Tax"
				disabled
				:modelValue="amountWithTax.toFixed(2)"
				type="number"
			/>
		</div>

		<div class="mt-4 flex w-full justify-end">
			<Button variant="solid" @click="onPayClick" :loading="paymentInProgress">
				Make payment via M-Pesa
			</Button>
		</div>

		<ErrorMessage v-if="errorMessage" :message="errorMessage" />
	</div>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../../../utils/error';
import { frappeRequest, ErrorMessage } from 'frappe-ui';
export default {
	name: 'BuyPrepaidCreditsMpesa',
	props: {
		amount: {
			type: Number,
			required: true,
		},
		amountKES: {
			type: Number,
			required: true,
			default: 1,
		},
		minimumAmount: {
			type: Number,
			required: true,
			default: 10,
		},
		exchangeRate: {
			type: Number,
			required: true,
			default: 129,
		},
	},
	data() {
		return {
			paymentErrorMessage: null,
			errorMessage: null,
			paymentInProgress: false,
			partnerInput: '',
			phoneNumberInput: this.$team.doc.mpesa_phone_number || '',
			taxIdInput: this.$team.doc.mpesa_tax_id || '',
			teams: [],
			taxPercentage: 1,
			amountWithTax: 0,
			showTaxInfo: false,
			maximumAmount: 150000,
		};
	},
	resources: {
		requestForPayment() {
			return {
				url: 'press.api.billing.request_for_payment',
				params: {
					request_amount: this.amountKES,
					sender: this.phoneNumberInput,
					partner: this.getPartnerValue(),
					tax_id: this.taxIdInput,
					amount_with_tax: this.amountWithTax,
					phone_number: this.phoneNumberInput,
					amount_usd: this.amount,
					exchange_rate: this.exchangeRate,
				},
				validate() {
					const pattern = /^[A-Z]\d{9}[A-Z]$/;
					if (this.amount < this.minimumAmount) {
						throw new DashboardError(
							`Amount is less than the minimum allowed: ${this.minimumAmount}`,
						);
					}
					if (this.amount > this.maximumAmount) {
						throw new DashboardError(
							`Amount is more than the maximum allowed: ${this.maximumAmount}`,
						);
					}
					const partnerValue = this.getPartnerValue();
					if (!partnerValue || !this.phoneNumberInput) {
						throw new DashboardError(
							'Both partner and phone number are required for payment.',
						);
					}
					if (!this.taxIdInput) {
						throw new DashboardError('Tax ID is required for payment.');
					}
					if (this.taxIdInput && !pattern.test(this.taxIdInput)) {
						throw new DashboardError('Invalid Tax Id');
					}
				},
				async onSuccess(data) {
					if (data?.ResponseCode === '0') {
						toast.success(
							data.ResponseDescription ||
								'Please follow the instructions on your phone',
						);
					} else {
						toast.error(
							data.ResponseDescription ||
								'Something went wrong. Please try again.',
						);
					}
				},
			};
		},
	},
	methods: {
		getPartnerValue() {
			if (!this.partnerInput) return null;
			if (typeof this.partnerInput === 'object' && this.partnerInput !== null) {
				return this.partnerInput.value || this.partnerInput;
			}
			return this.partnerInput;
		},
		async onPayClick() {
			this.paymentInProgress = true;
			try {
				const response = await this.$resources.requestForPayment.submit();
				if (response.ResponseCode === '0') {
					toast.success(
						response.Success ||
							'Payment Initiated successfully, check your phone for instructions',
					);
					this.$emit('success');
				} else {
					throw new Error(response.ResponseDescription || 'Payment failed');
				}
			} catch (error) {
				this.paymentErrorMessage =
					error.message || 'Payment failed. Please try again.';
				toast.error(this.paymentErrorMessage);
			} finally {
				this.paymentInProgress = false;
			}
		},
		async fetchTeams() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.display_mpesa_payment_partners',
					method: 'GET',
				});
				if (Array.isArray(response)) {
					this.teams = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch teams ${error.message}`;
			}
		},
		totalAmountWithTax() {
			const amountWithTax =
				this.amountKES + (this.amountKES * this.taxPercentage) / 100;
			this.amountWithTax = Math.round(amountWithTax);
		},
		async fetchTaxPercentage() {
			try {
				const taxPercentage = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.get_tax_percentage',
					method: 'GET',
					params: {
						payment_partner: this.getPartnerValue(),
					},
				});
				this.taxPercentage = taxPercentage;
			} catch (error) {
				this.errorMessage = `Failed to fetch tax percentage ${error.message}`;
			}
		},
	},
	watch: {
		partnerInput() {
			this.fetchTaxPercentage();
			this.totalAmountWithTax();
			this.showTaxInfo = true;
		},
		amountKES() {
			this.totalAmountWithTax();
		},
		taxPercentage() {
			this.totalAmountWithTax();
		},
	},
	mounted() {
		this.fetchTeams();
	},
};
</script>
