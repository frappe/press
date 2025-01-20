<template
	v-if="$team.doc.country === 'Kenya' && $team.doc.erpnext_partner === 1"
>
	<div>
		<label class="block mt-4">
			<span class="text-sm leading-4 text-gray-700"> </span>
			<ErrorMessage class="mt-1" :message="paymentErrorMessage" />
		</label>

		<ErrorMessage class="mt-2" :message="errorMessage" />

		<FormControl
			type="autocomplete"
			:options="teams"
			size="sm"
			variant="subtle"
			placeholder="Select a partner"
			:disabled="false"
			label="Select Partner"
			v-model="partnerInput"
			class="mb-5"
		/>

		<FormControl
			label="M-Pesa Phone Number"
			v-model.number="phoneNumberInput"
			name="phone_number"
			autocomplete="off"
			class="mb-5"
			type="tel"
			placeholder="Enter phone number"
		/>

		<FormControl
			label="Tax ID"
			v-model="taxIdInput"
			name="tax_id"
			autocomplete="off"
			class="mb-5"
			type="string"
			placeholder="Enter company's Tax ID"
		/>

		<!-- Show amount after tax -->
		<div v-if="showTaxInfo">
			<div class="mt-4">
				<p class="text-sm leading-4 text-gray-700">Tax(%):</p>
				<p class="text-md text-black-100 bg-gray-100 rounded-sm">
					{{ taxPercentage }}%
				</p>
			</div>

			<div class="mt-4">
				<p class="text-sm leading-4 text-gray-700">Total Amount With Tax:</p>
				<p class="text-md text-black-100 bg-gray-100 rounded-sm">
					Ksh. {{ amountWithTax }}
				</p>
			</div>
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
import { DashboardError } from '../utils/error';
import { ErrorMessage } from 'frappe-ui';
import { frappeRequest } from 'frappe-ui';
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
	},
	data() {
		return {
			paymentErrorMessage: null,
			errorMessage: null,
			paymentInProgress: false,
			partnerInput: '',
			phoneNumberInput: '',
			taxIdInput: '',
			teams: [],
			taxPercentage: 1,
			amountWithTax: 0,
			showTaxInfo: false,
			exchangeRate: 0,
		};
	},
	resources: {
		requestForPayment() {
			return {
				url: 'press.api.billing.request_for_payment',
				params: {
					request_amount: this.amountKES,
					sender: this.phoneNumberInput,
					partner: this.partnerInput.value,
					tax_id: this.taxIdInput,
					amount_with_tax: this.amountWithTax,
					phone_number: this.phoneNumberInput,
				},
				validate() {
					if (this.amount < this.minimumAmount) {
						throw new DashboardError(
							`Amount is less than the minimum allowed: ${this.minimumAmount}`,
						);
					}
					if (!this.partnerInput || !this.phoneNumberInput) {
						throw new DashboardError(
							'Both partner and phone number are required for payment.',
						);
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
		async fetchTaxId() {
			try {
				const taxId = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.get_tax_id',
					method: 'GET',
				});
				if (taxId) {
					this.taxIdInput = taxId;
				} else {
					this.taxIdInput = '';
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch tax ID: ${error.message}`;
			}
		},
		async fetchPhoneNo() {
			try {
				const phoneNo = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.get_phone_no',
					method: 'GET',
				});
				if (phoneNo) {
					this.phoneNumberInput = phoneNo;
				} else {
					this.phoneNumberInput = '';
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch tax ID: ${error.message}`;
			}
		},
		async fetchTaxPercentage() {
			try {
				const taxPercentage = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.get_tax_percentage',
					method: 'GET',
					params: {
						payment_partner: this.partnerInput.value,
					},
				});
				this.taxPercentage = taxPercentage;
			} catch (error) {
				this.errorMessage = `Failed to fetch tax percentage ${error.message}`;
			}
		},
		totalAmountWithTax() {
			const amountWithTax =
				this.amountKES + (this.amountKES * this.taxPercentage) / 100;
			this.amountWithTax = amountWithTax;
		},
		async fetchExchangeRate() {
			try {
				const exchangeRate = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.get_exchange_rate',
					method: 'GET',
					params: {
						from_currency: 'KES',
						to_currency: 'USD',
					},
				});
				this.exchangeRate = exchangeRate;
			} catch (error) {
				this.errorMessage = `Failed to fetch exchange rate ${error.message}`;
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
		this.fetchTaxId();
		this.fetchPhoneNo();
	},
};
</script>
