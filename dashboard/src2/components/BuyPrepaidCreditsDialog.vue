<template>
	<Dialog
		:options="{ title: 'Add money to your account' }"
		v-model="showDialog"
	>
		<template v-slot:body-content>
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
							{{ $team.doc.currency === 'INR' ? '₹' : '$' }}
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
				<div class="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
					<button
						v-if="$team.doc.currency === 'INR' || $team.doc.razorpay_enabled"
						@click="paymentGateway = 'Razorpay'"
						label="Razorpay"
						class="flex h-10 items-center justify-center rounded border"
						:class="{
							'border-gray-300': paymentGateway !== 'Razorpay',
							'border-gray-900 ring-1 ring-gray-900':
								paymentGateway === 'Razorpay'
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
							'border-gray-900 ring-1 ring-gray-900':
								paymentGateway === 'Stripe'
						}"
					>
						<img
							class="h-7 w-24"
							:src="`/assets/press/images/stripe-logo.svg`"
							alt="Stripe Logo"
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
				@success="onSuccess"
				@cancel="onCancel"
			/>
		</template>
	</Dialog>
</template>
<script>
import BuyPrepaidCreditsStripe from './BuyPrepaidCreditsStripe.vue';
import BuyPrepaidCreditsRazorpay from './BuyPrepaidCreditsRazorpay.vue';

export default {
	name: 'BuyPrepaidCreditsDialog',
	components: {
		BuyPrepaidCreditsStripe,
		BuyPrepaidCreditsRazorpay
	},
	data() {
		return {
			paymentGateway: null,
			creditsToBuy: this.minimumAmount
		};
	},
	mounted() {
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
		}
	},
	emits: ['update:modelValue', 'success'],
	methods: {
		onSuccess() {
			this.$emit('success');
		},
		onCancel() {
			this.showDialog = false;
		}
	},
	computed: {
		totalAmount() {
			if (this.$team.doc.currency === 'INR') {
				return (
					this.creditsToBuy +
					this.creditsToBuy * (this.$team.doc.billing_info.gst_percentage || 0)
				).toFixed(2);
			} else {
				return this.creditsToBuy;
			}
		},
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
