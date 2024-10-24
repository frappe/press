<template>
	<div>
		<FormControl
			:label="`Amount (Minimum Amount: ${minimumAmount})`"
			class="mb-3"
			v-model.number="creditsToBuy"
			name="amount"
			autocomplete="off"
			type="number"
			:min="minimumAmount"
		>
			<template #prefix>
				<div class="grid w-4 place-items-center text-sm text-gray-700">
					<!--Test Currency, but will add KES for kenya and GBP for Egypt-->
					{{ $team.doc.currency === 'INR' ? '₹' : $team.doc.currency === 'KES' ? 'Ksh' : '$' }}
				</div>
			</template>
		</FormControl>
		<!-- New Conditional Field -->
		<FormControl
			v-if="$team.doc.currency === 'KES' || paymentGateway === 'Mpesa'"
			:label="`Amount in KES`"
			class="mb-3"
			v-model.number="creditsToBuyKES"
			name="amount_kes"
			autocomplete="off"
			type="number"
			:disabled="true"
			:min="minimumAmountKES"
		>
			<template #prefix>
				<div class="grid w-3 place-items-center text-sm text-gray-700">
					{{paymentGateway === 'Mpesa' ? 'Ksh.' : '$'  }}
				</div>
			</template>
		</FormControl>
		<FormControl
			v-if="$team.doc.currency === 'INR'"
			:label="`Total Amount + GST (${
				$team.doc?.billing_info.gst_percentage * 100
			}%)`"
			disabled
			:modelValue="totalAmount"
			name="total"
			autocomplete="off"
			type="number"
		>
			<template #prefix>
				<div class="grid w-4 place-items-center text-sm text-gray-700">
					{{ $team.doc.currency === 'INR' ? '₹' : '$' }}
				</div>
			</template>
		</FormControl> 

	</div>

	<div class="mt-4">
		<div class="text-xs text-gray-600">Select Payment Gateway</div>
		<h1></h1>
		<div class="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
			<button
				v-if="$team.doc.currency === 'INR' || $team.doc.razorpay_enabled"
				@click="paymentGateway = 'Razorpay'"
				label="Razorpay"
				class="flex h-10 items-center justify-center rounded border"
				:class="{
					'border-gray-300': paymentGateway !== 'Razorpay',
					'border-gray-900 ring-1 ring-gray-900': paymentGateway === 'Razorpay'
				}"
			>
				<img
					class="w-24"
					:src="`/assets/press/images/razorpay-logo.svg`"
					alt="Razorpay Logo"
				/>
			</button>
			<button
				@click="paymentGateway = 'Stripe'"
				label="Stripe"
				class="flex h-10 items-center justify-center rounded border"
				:class="{
					'border-gray-300': paymentGateway !== 'Stripe',
					'border-gray-900 ring-1 ring-gray-900': paymentGateway === 'Stripe'
				}"
			>
				<img
					class="h-7 w-24"
					:src="`/assets/press/images/stripe-logo.svg`"
					alt="Stripe Logo"
				/>
			</button>
			<!-- Paymob button -->
			<button
				@click="paymentGateway = 'Paymob'"
				label="Paymob"
				class="flex h-10 items-center justify-center rounded border"
				:class="{
					'border-gray-300': paymentGateway !== 'Paymob',
					'border-gray-900 ring-1 ring-gray-900': paymentGateway === 'Paymob'
				}"
			>
				<img
					class="h-7 w-24"
					:src="`/assets/press/images/paymobLogo.png`"
					alt="Paymob Logo"
				/>
			</button>

			<!--M-Pesa button-->
			<button 
			v-if="$team.doc.country === 'Kenya'"
			@click="paymentGateway = 'Mpesa'"
			label="Mpesa"
			class="flex h-10 items-center justify-center rounded border"
			:class="{
				'border-gray-300': paymentGateway !== 'Mpesa',
				'border-gray-900 ring-1 ring-gray-900': paymentGateway === 'Mpesa'
			}"
			>
			<img
					class="h-7 w-24"
					:src="`/assets/press/images/mpesa.svg`"
					alt="M-pesa Logo"
				/>
		</button>
		</div>
	</div>

	<BuyPrepaidCreditsStripe
		v-if="paymentGateway === 'Stripe'"
		:amount="creditsToBuy"
		:minimumAmount="minimumAmount"
		@success="onSuccess"
		@cancel="onCancel"
	/>

	<BuyPrepaidCreditsRazorpay
		v-if="paymentGateway === 'Razorpay'"
		:amount="creditsToBuy"
		:minimumAmount="minimumAmount"
		:isOnboarding="isOnboarding"
		@success="onSuccess"
		@cancel="onCancel"
	/>

	<!--M-pesa-->
	<BuyPrepaidCreditMpesa
	v-if="paymentGateway === 'Mpesa'"
	:amount="creditsToBuy"
	:amountKES="creditsToBuyKES"
	:minimumAmount="minimumAmount"
	@success="onSuccess"
	@cancel="onCancel"
	/>

	<!-- Paymob -->
	<BuyPrepaidCreditsPaymob
		v-if="paymentGateway === 'Paymob'"
		:amount="creditsToBuy"
		:minimumAmount="minimumAmount"
	/>

	
	
</template>
<script>
import BuyPrepaidCreditsStripe from './BuyPrepaidCreditsStripe.vue';
import BuyPrepaidCreditsRazorpay from './BuyPrepaidCreditsRazorpay.vue';
import BuyPrepaidCreditMpesa from './BuyPrepaidCreditMpesa.vue';
import BuyPrepaidCreditsPaymob from './BuyPrepaidCreditsPaymob.vue';
import { frappeRequest } from 'frappe-ui';


export default {
	name: 'BuyPrepaidCreditsDialog',
	components: {
		BuyPrepaidCreditsStripe,
		BuyPrepaidCreditsRazorpay,
		BuyPrepaidCreditMpesa,
		BuyPrepaidCreditsPaymob,
	},
	data() {
		return {
			paymentGateway: null,
			creditsToBuy: this.minimumAmount,
			creditsToBuyKES:1300,
			exchangeRate:1,
		};
	},

	watch: {
	creditsToBuy(newValue) {
		const computedKES = (newValue * this.exchangeRate);
		if (this.creditsToBuyKES !== computedKES) {
			this.creditsToBuyKES = computedKES;
		}
	},
	// Watch for KES Input (creditsToBuyKES)
	creditsToBuyKES(newValue) {
		const computedUSD = (newValue / this.exchangeRate);
		if (this.creditsToBuy !== computedUSD) {
			this.creditsToBuy = computedUSD;
		}
	}
},

	mounted() {
		this.fetchExchangeRate();
		if (this.$team.doc.currency === 'USD' && !this.$team.doc.razorpay_enabled) {
			this.paymentGateway = 'Stripe';
		}
	},
	props: {
		modelValue: {
			default: false
		},
		minimumAmount: {
			type: Number,
			default: 0
		},
		isOnboarding: {
			type: Boolean,
			default: false
		}
	},
	emits: ['success'],
	methods: {
		onSuccess() {
			this.$emit('success');
		},
		onCancel() {
			this.$emit('cancel');
		},
		async fetchExchangeRate() {
			try {
				const data = await frappeRequest({
					url: 'press.api.billing.get_exchange_rate',
					params: {
						from_currency: 'USD',
						to_currency: 'KES'
					}
				});
				this.exchangeRate = data;
			} catch (error) {
				console.error(error);
			}
		}
	},

	computed: {
		totalAmount() {
			let creditsToBuy = this.creditsToBuy || 0;
			if (this.$team.doc.currency === 'INR') {
				return (
					creditsToBuy +
					creditsToBuy * (this.$team.doc.billing_info.gst_percentage || 0)
				).toFixed(2);
			} else {
				return creditsToBuy;
			}
		}
	}
};
</script>
