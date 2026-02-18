<template>
	<div>
		<!-- Amount -->
		<div>
			<FormControl
				:label="`Amount (Minimum Amount: ${maximumAmount})`"
				class="mb-3"
				v-model.number="creditsToBuy"
				name="amount"
				autocomplete="off"
				type="number"
				:max="maximumAmount"
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
				autocomplete="off"
				type="number"
			>
				<template #prefix>
					<div class="grid w-4 place-items-center text-sm text-gray-700">
						{{ team.doc.currency === 'INR' ? '₹' : '$' }}
					</div>
				</template>
			</FormControl>
		</div>

		<!-- Payment Gateway -->
		<div class="mt-4">
			<div class="text-xs text-gray-600">Select Payment Gateway</div>
			<div class="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
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
					v-if="team.doc.currency === 'USD' && paypalEnabled.data"
					size="lg"
					:class="{
						'border-[1.5px] border-gray-700': paymentGateway === 'Razorpay',
					}"
					@click="paymentGateway = 'Razorpay'"
				>
					<PayPalLogo class="h-7 w-20" />
				</Button>
			</div>
		</div>

		<!-- Payment Button -->
		<BuyPartnerCreditsStripe
			v-if="paymentGateway === 'Stripe'"
			:amount="creditsToBuy"
			:maximumAmount="maximumAmount"
			@success="() => emit('success')"
			@cancel="show = false"
		/>

		<BuyPartnerCreditsRazorpay
			v-if="paymentGateway === 'Razorpay'"
			:amount="creditsToBuy"
			:maximumAmount="maximumAmount"
			:paypalEnabled="paypalEnabled.data"
			type="Partnership Fee"
			@success="() => emit('success')"
			@cancel="show = false"
		/>
	</div>
</template>
<script setup>
import BuyPartnerCreditsStripe from './BuyPartnerCreditsStripe.vue';
import BuyPartnerCreditsRazorpay from './BuyPartnerCreditsRazorpay.vue';
import RazorpayLogo from '../../logo/RazorpayLogo.vue';
import StripeLogo from '../../logo/StripeLogo.vue';
import PayPalLogo from '../../logo/PayPalLogo.vue';
import {
	FormControl,
	Button,
	createDocumentResource,
	createResource,
} from 'frappe-ui';
import { ref, computed, inject, defineEmits } from 'vue';

const emit = defineEmits(['success']);

const team = inject('team');

const paypalEnabled = createResource({
	url: 'press.api.billing.is_paypal_enabled',
	cache: 'paypalEnabled',
	auto: true,
});

const pressSettings = createDocumentResource({
	doctype: 'Press Settings',
	name: 'Press Settings',
	auto: true,
	initialData: {},
});

const maximumAmount = computed(() => {
	if (!pressSettings.doc) return 0;
	const feeAmount =
		team.doc?.currency == 'INR'
			? pressSettings.doc.partnership_fee_inr
			: pressSettings.doc.partnership_fee_usd;
	return Math.ceil(feeAmount);
});

const creditsToBuy = ref(maximumAmount.value);
const paymentGateway = ref('');

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
</script>
