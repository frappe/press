<template>
	<div>
		<span
			v-if="team.doc.currency === 'INR' || showPaypal"
			class="mt-2.5 inline-flex gap-2 text-base text-gray-700"
		>
			<FeatherIcon name="info" class="my-1 h-4" />
			<span class="leading-5" v-if="team.doc.currency === 'INR'">
				If you select Razorpay, you can pay using Credit Card, Debit Card, Net
				Banking, UPI, Wallets, etc. If you are using Net Banking, it may take
				upto 5 days for balance to reflect.
			</span>
			<span class="leading-5" v-if="showPaypal">
				You can pay using your PayPal account. Processing may take a few minutes
				for the balance to reflect.
			</span>
		</span>
		<ErrorMessage class="mt-3" :message="createRazorpayOrder.error" />
		<div class="mt-8">
			<Button
				v-if="!isPaymentComplete"
				class="w-full"
				size="md"
				variant="solid"
				:label="`Proceed to payment using ${showPaypal ? 'PayPal' : 'Razorpay'}`"
				:loading="createRazorpayOrder.loading"
				@click="createRazorpayOrder.submit()"
			/>
			<Button
				v-else
				class="w-full"
				size="md"
				label="Confirming payment"
				variant="solid"
				:loading="isVerifyingPayment"
			/>
		</div>
	</div>
</template>
<script setup>
import { Button, ErrorMessage, FeatherIcon, createResource } from 'frappe-ui';
import { ref, computed, onMounted, onBeforeUnmount, inject } from 'vue';
import { toast } from 'vue-sonner';
import { DashboardError } from '../../utils/error';

const props = defineProps({
	amount: {
		type: Number,
		default: 0,
	},
	maximumAmount: {
		type: Number,
		default: 0,
	},
	type: {
		type: String,
		default: 'Prepaid Credits',
	},
	paypalEnabled: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['success']);
const team = inject('team');

const showPaypal = computed(() => {
	return team.doc.currency === 'USD' && props.paypalEnabled;
});

const isPaymentComplete = ref(false);
const isVerifyingPayment = ref(false);

const razorpayCheckoutJS = ref(null);

onMounted(() => {
	razorpayCheckoutJS.value = document.createElement('script');
	razorpayCheckoutJS.value.setAttribute(
		'src',
		'https://checkout.razorpay.com/v1/checkout.js',
	);
	razorpayCheckoutJS.value.async = true;
	document.head.appendChild(razorpayCheckoutJS.value);
});

onBeforeUnmount(() => {
	razorpayCheckoutJS.value?.remove();
});

let order_type = props.type;

const createRazorpayOrder = createResource({
	url: 'press.api.billing.create_razorpay_order',
	params: {
		amount: props.amount,
		transaction_type: order_type,
	},
	onSuccess: (data) => processOrder(data),
	validate: () => {
		if (props.amount > props.maximumAmount) {
			throw new DashboardError('Amount more than maximum amount required');
		}
	},
});

const handlePaymentFailed = createResource({
	url: 'press.api.billing.handle_razorpay_payment_failed',
	onSuccess: () => {
		console.log('Payment Failed.');
	},
});

function processOrder(data) {
	const options = {
		key: data.key_id,
		order_id: data.order_id,
		name: 'Frappe Cloud',
		image: 'https://frappe.io/files/cloud.png',
		prefill: { email: team.doc?.user },
		handler: handlePaymentSuccess,
		theme: { color: '#171717' },
		...(showPaypal.value
			? {
					config: {
						display: {
							blocks: {
								wallets: {
									name: 'Pay using PayPal',
									instruments: [
										{
											method: 'wallet',
											wallets: ['paypal'],
										},
									],
								},
							},
							sequence: ['block.wallets'],
							preferences: {
								show_default_blocks: false,
							},
						},
					},
				}
			: {}),
	};

	const rzp = new Razorpay(options);

	// Opens the payment checkout frame
	rzp.open();

	// Attach failure handler
	rzp.on('payment.failed', handlePaymentFailure);
	// rzp.on('payment.success', this.handlePaymentSuccess);
}

function handlePaymentFailure(response) {
	handlePaymentFailed.submit({ response });
	toast.error('Payment failed');
}

function handlePaymentSuccess() {
	isPaymentComplete.value = true;
	emit('success');
	toast.success('Payment successful');
}
</script>
