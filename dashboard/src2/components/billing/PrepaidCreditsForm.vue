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
					<div class="grid w-4 place-items-center text-sm text-gray-700">
						{{ team.doc.currency === 'INR' ? '₹' : '$' }}
					</div>
				</template>
			</FormControl>
			<FormControl
				v-if="team.doc.currency === 'INR'"
				:label="`Total Amount + GST (${
					team.doc?.billing_info.gst_percentage * 100
				}%)`"
				disabled
				:modelValue="totalAmount"
				name="total"
				type="number"
			>
				<template #prefix>
					<div class="grid w-4 place-items-center text-sm text-gray-700">
						{{ team.doc.currency === 'INR' ? '₹' : '$' }}
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
					<div class="-ml-1 grid w-4 place-items-center text-sm text-gray-700">
						{{ 'Ksh' }}
					</div>
				</template>
			</FormControl>
		</div>

		<!-- Payment Gateway -->
		<div class="mt-4">
			<div class="text-xs text-gray-600">Select Payment Gateway</div>
			<div class="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
				<Button
					v-if="team.doc.currency === 'INR' || team.doc.razorpay_enabled"
					size="lg"
					:class="{
						'border-[1.5px] border-gray-700': paymentGateway === 'Razorpay',
					}"
					@click="paymentGateway = 'Razorpay'"
				>
					<RazorpayLogo class="w-24" />
				</Button>
				<Button
					size="lg"
					:class="{
						'border-[1.5px] border-gray-700': paymentGateway === 'Stripe',
					}"
					@click="paymentGateway = 'Stripe'"
				>
					<StripeLogo class="h-7 w-24" />
				</Button>
				<Button
					v-if="team.doc.country === 'Kenya' && team.doc.mpesa_enabled"
					size="lg"
					:class="{
						'border-[1.5px] border-gray-700': paymentGateway === 'M-Pesa',
					}"
					@click="paymentGateway = 'M-Pesa'"
				>
					<img
						class="h-14 w-24"
						:src="`/assets/press/images/mpesa-logo.svg`"
						alt="M-pesa Logo"
					/>
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
	</div>
</template>
<script setup>
import BuyCreditsStripe from './BuyCreditsStripe.vue';
import BuyCreditsRazorpay from './BuyCreditsRazorpay.vue';
import RazorpayLogo from '../../logo/RazorpayLogo.vue';
import StripeLogo from '../../logo/StripeLogo.vue';
import BuyPrepaidCreditsMpesa from './mpesa/BuyPrepaidCreditsMpesa.vue';
import { FormControl, Button, createResource } from 'frappe-ui';
import { ref, computed, inject, watch, onMounted } from 'vue';

const emit = defineEmits(['success']);

const team = inject('team');
const props = defineProps({
	minimumAmount: Number,
});

const totalUnpaidAmount = createResource({
	url: 'press.api.billing.total_unpaid_amount',
	cache: 'totalUnpaidAmount',
	auto: true,
});

const minimumAmount = computed(() => {
	if (props.minimumAmount) return props.minimumAmount;
	if (!team.doc) return 0;
	const unpaidAmount = totalUnpaidAmount.data || 0;
	const minimumDefault = team.doc?.currency == 'INR' ? 410 : 5;

	return Math.ceil(
		unpaidAmount && unpaidAmount > 0 ? unpaidAmount : minimumDefault,
	);
});

const creditsToBuy = ref(minimumAmount.value);
const paymentGateway = ref('');

watch(minimumAmount, () => {
	creditsToBuy.value = minimumAmount.value;
});

const totalAmount = computed(() => {
	const _creditsToBuy = creditsToBuy.value || 0;

	if (team.doc?.currency === 'INR') {
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
