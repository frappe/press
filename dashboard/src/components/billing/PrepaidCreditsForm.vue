<template>
	<div>
		<!-- Amount -->
		<div>
			<FormControl
				:label="`Amount (Minimum Amount: ${minimumAmount})`"
				class="mb-3"
				v-model.number="creditsToBuy"
				name="amount"
				type="number"
				:min="minimumAmount"
			>
				<template #prefix>
					<div class="grid w-4 place-items-center text-sm text-ink-gray-7">
						{{ team.doc.currency === 'DZD' ? 'د.ج' : '$' }}
					</div>
				</template>
			</FormControl>
			<FormControl
				v-if="team.doc.currency === 'DZD'"
				:label="`Montant total + TVA (${
					(team.doc?.billing_info?.tva_percentage || 0) * 100
				}%)`"
				disabled
				:modelValue="totalAmount"
				name="total"
				type="number"
			>
				<template #prefix>
					<div class="grid w-4 place-items-center text-sm text-ink-gray-7">
						{{ team.doc.currency === 'DZD' ? 'د.ج' : '$' }}
					</div>
				</template>
			</FormControl>
			<FormControl
				v-if="team.doc.country === 'Kenya' && paymentGateway === 'M-Pesa'"
				:label="`Amount in KES (Exchange Rate: ${Math.round(
					exchangeRate,
				)} against 1 USD)`"
				disabled
				:modelValue="amountInKES"
				name="amount_in_kes"
				type="number"
			>
				<template #prefix>
					<div class="-ml-1 grid w-4 place-items-center text-sm text-ink-gray-7">
						{{ 'Ksh' }}
					</div>
				</template>
			</FormControl>
		</div>

		<!-- Payment Gateway -->
		<div class="mt-4">
			<div class="text-xs text-ink-gray-6">Passerelle de paiement</div>
			<div class="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
				<Button
					v-if="team.doc.currency === 'DZD'"
					size="lg"
					:class="{
						'border-[1.5px] border-gray-700': paymentGateway === 'Chargily',
					}"
					@click="paymentGateway = 'Chargily'"
				>
					<ChargilyLogo class="w-24" />
				</Button>
			</div>
		</div>

		<!-- Payment Button -->
		<BuyCreditsStripe
			v-if="paymentGateway === 'Stripe'"
			:amount="creditsToBuy"
			:minimumAmount="minimumAmount"
			@success="() => emit('success')"
			@cancel="show = false"
		/>

		<BuyCreditsRazorpay
			v-if="paymentGateway === 'Razorpay'"
			:amount="creditsToBuy"
			:minimumAmount="minimumAmount"
			:paypalEnabled="paypalEnabled.data"
			:type="props.type"
			:docName="props.docName"
			@success="() => emit('success')"
			@cancel="show = false"
		/>

		<BuyPrepaidCreditsMpesa
			v-if="paymentGateway === 'M-Pesa'"
			:amount="creditsToBuy"
			:amountKES="amountInKES"
			:minimumAmount="minimumAmount"
			:exchangeRate="exchangeRate"
			@success="() => emit('success')"
			@cancel="show = false"
		/>

		<BuyCreditsChargily
			v-if="paymentGateway === 'Chargily'"
			:amount="creditsToBuy"
			:minimumAmount="minimumAmount"
			@success="() => emit('success')"
		/>
	</div>
</template>
<script setup>
import BuyCreditsStripe from './BuyCreditsStripe.vue';
import BuyCreditsRazorpay from './BuyCreditsRazorpay.vue';
import BuyCreditsChargily from './BuyCreditsChargily.vue';
import RazorpayLogo from '../../logo/RazorpayLogo.vue';
import PayPalLogo from '../../logo/PayPalLogo.vue';
import StripeLogo from '../../logo/StripeLogo.vue';
import ChargilyLogo from '../../logo/ChargilyLogo.vue';
import BuyPrepaidCreditsMpesa from './mpesa/BuyPrepaidCreditsMpesa.vue';
import { FormControl, Button, createResource } from 'frappe-ui';
import { ref, computed, inject, watch, onMounted } from 'vue';

const emit = defineEmits(['success']);

const team = inject('team');
const props = defineProps({
	minimumAmount: {
		type: Number,
		default: null,
	},
	type: {
		type: String,
		default: 'Prepaid Credits',
	},
	docName: {
		type: String,
		default: null,
	},
});

const paypalEnabled = createResource({
	url: 'press.api.billing.is_paypal_enabled',
	cache: 'paypalEnabled',
	auto: true,
});

const totalUnpaidAmount = createResource({
	url: 'press.api.billing.total_unpaid_amount',
	cache: 'totalUnpaidAmount',
	auto: true,
});

const minimumAmount = computed(() => {
	if (props.minimumAmount) return props.minimumAmount;
	if (!team.doc) return 0;
	let unpaidAmount = totalUnpaidAmount.data || 0;
	const minimumDefault = team.doc?.currency == 'DZD' ? 410 : 5;

	if (unpaidAmount > 100000 && team.doc?.currency == 'DZD') {
		unpaidAmount = 100000;
	} else if (unpaidAmount > 1450 && team.doc?.currency == 'USD') {
		unpaidAmount = 1450;
	}

	return Math.ceil(
		unpaidAmount && unpaidAmount > 0 ? unpaidAmount : minimumDefault,
	);
});

const creditsToBuy = ref(minimumAmount.value);
const paymentGateway = ref('');

watch(totalUnpaidAmount, () => {
	creditsToBuy.value =
		totalUnpaidAmount.data > 0 ? totalUnpaidAmount.data : minimumAmount.value;
});

const totalAmount = computed(() => {
	const _creditsToBuy = creditsToBuy.value || 0;

	if (team.doc?.currency === 'DZD') {
		return (
			_creditsToBuy +
			_creditsToBuy * (team.doc.billing_info.gst_percentage || 0)
		).toFixed(2);
	} else {
		return _creditsToBuy;
	}
});

const amountInKES = ref();
const exchangeRate = ref(0);

watch(creditsToBuy, () => {
	let _amountInKES = creditsToBuy.value * exchangeRate.value;
	if (
		paymentGateway.value === 'M-Pesa' &&
		_amountInKES !== creditsToBuy.value
	) {
		amountInKES.value = _amountInKES;
	}
});

watch(amountInKES, () => {
	let data = amountInKES.value / exchangeRate.value;
	if (paymentGateway.value === 'M-Pesa' && data !== creditsToBuy.value) {
		creditsToBuy.value = data;
	}
});

watch(paymentGateway, () => {
	if (paymentGateway.value === 'M-Pesa') {
		amountInKES.value = creditsToBuy.value * exchangeRate.value;
	}
});

const fetchExchangeRate = async () => {
	try {
		const fromCurrency = 'usd';
		const toCurrency = 'kes';
		const baseURL = `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies`;
		const URL = `${baseURL}/${fromCurrency}.json`;
		let response = await fetch(URL);
		let responseJSON = await response.json();
		let rate = responseJSON[fromCurrency][toCurrency];
		exchangeRate.value = Math.round(rate);
	} catch (error) {
		console.error(error);
	}
};

onMounted(() => {
	fetchExchangeRate();
});
</script>
