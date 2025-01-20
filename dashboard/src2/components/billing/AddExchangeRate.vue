<template>
	<Dialog :options="{ title: 'Add Currency Exchange', size: 'lg' }">
		<template #body-content>
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					label="From Currency"
					v-model="fromCurrency"
					type="autocomplete"
					variant="subtle"
					:disabled="false"
					:options="currencySymbols"
					name="from_currency"
					class="mb-5"
					required
				/>

				<FormControl
					label="To Currency"
					v-model="toCurrency"
					name="to_currency"
					type="autocomplete"
					variant="subtle"
					:disabled="false"
					:options="currencySymbols"
					class="mb-5"
					required
				/>

				<FormControl
					label="Exchange Rate"
					v-model="exchangeRate"
					name="exchange_rate"
					autocomplete="off"
					class="mb-5"
					type="number"
					required
				/>

				<DatePicker
					v-model="date"
					variant="subtle"
					name="date"
					placeholder="Placeholder"
					:disabled="false"
					label="Date"
				/>
			</div>

			<div class="mt-4 flex w-full items-center justify-center">
				<Button
					@click="saveExchangeRate"
					class="justify-center w-full font-bold"
					variant="solid"
					type="primary"
					>Add Currency Exchange</Button
				>
			</div>
		</template>
		<ErrorMessage class="mt-2" :message="ErrorMessage" />
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { frappeRequest } from 'frappe-ui';
import { DashboardError } from '../../utils/error';
import FormControl from 'frappe-ui/src/components/FormControl.vue';
import DatePicker from 'frappe-ui/src/components/DatePicker.vue';
import ErrorMessage from 'frappe-ui/src/components/ErrorMessage.vue';

export default {
	name: 'AddExchangeRate',
	components: { DatePicker },
	data() {
		return {
			fromCurrency: '',
			toCurrency: '',
			date: '',
			exchangeRate: '',
			currencySymbols: [],
		};
	},

	resources: {
		addCurrencyExchange() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.create_exchange_rate',
				params: {
					from_currency: this.fromCurrency,
					to_currency: this.toCurrency,
					exchange_rate: this.exchangeRate,
					date: this.date,
				},
				validate() {
					if (
						!this.fromCurrency ||
						!this.toCurrency ||
						!this.exchangeRate ||
						!this.date
					) {
						toast.error('All fields are required');
						return false;
					}
				},
				async onSuccess() {
					if (data) {
						toast.success('Currency Exchange Added Successfully');
						this.$emit('close');
					} else {
						toast.error('Failed to add currency exchange');
					}
				},
			};
		},
	},

	methods: {
		async saveExchangeRate() {
			try {
				const response = await this.$resources.addCurrencyExchange.submit();
				if (response) {
					this.$toast.success('Currency Exchange Added Successfully');
					this.fromCurrency = '';
					this.toCurrency = '';
					this.exchangeRate = '';
					this.date = '';
				}
				this.$emit('closeDialog');
			} catch (error) {
				console.log(error);
				this.$toast.error(`Error adding currency exchange: ${error.message}`);
			}
		},

		async fetchCurrencySymbols() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.fetch_currencies',
					method: 'GET',
				});
				if (Array.isArray(response)) {
					this.currencySymbols = response;
				} else {
					this.ErrorMessage = 'No currency symbols found';
				}
			} catch (error) {
				this.ErrorMessage = `Error fetching currency symbols: ${error.message}`;
			}
		},
	},
	mounted() {
		this.fetchCurrencySymbols();
	},
};
</script>
