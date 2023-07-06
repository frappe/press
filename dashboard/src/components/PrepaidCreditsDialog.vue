<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:options="{
			title: 'Buy Credits',
			subtitle: paymentGateway ? '' : 'Choose your payment gateway'
		}"
	>
		<template v-slot:body-content>
			<BuyPrepaidCredits
				v-if="paymentGateway === 'stripe'"
				:minimumAmount="minimumAmount"
				@success="$emit('success')"
				@cancel="$emit('update:modelValue', false)"
			/>

			<div v-if="paymentGateway === 'razorpay'">
				<Input
					:label="`Amount (Minimum Amount: ${minimumAmount})`"
					v-model.number="creditsToBuy"
					name="amount"
					autocomplete="off"
					type="number"
					:min="minimumAmount"
				/>

				<p class="mt-3 text-xs">
					<span class="font-semibold">Note</span>: If you are using Net Banking,
					it may take upto 5 days for balance to reflect.
				</p>

				<ErrorMessage
					class="mt-3"
					:message="$resources.createRazorpayOrder.error"
				/>

				<div class="mt-4 flex w-full justify-between">
					<Button @click="paymentGateway = null">Go Back</Button>
					<div>
						<Button
							appearance="primary"
							:loading="$resources.createRazorpayOrder.loading"
							@click="buyCreditsWithRazorpay"
						>
							Buy
						</Button>
					</div>
				</div>
			</div>
			<div v-if="paymentGateway === 'midtrans'">
				<Input
					:label="`Amount (Minimum Amount: ${minimumAmount})`"
					v-model.number="creditsToBuy"
					name="amount"
					autocomplete="off"
					type="number"
					:min="minimumAmount"
				/>

				<!-- <p class="mt-3 text-xs">
					<span class="font-semibold">Note</span>: If you are using Net Banking,
					it may take upto 5 days for balance to reflect.
				</p> -->

				<ErrorMessage
					class="mt-3"
					:message="$resources.createMidTransToken.error"
				/>

				<div class="mt-4 flex w-full justify-between">
					<Button @click="paymentGateway = null">Go Back</Button>
					<div>
						<Button
							appearance="primary"
							:loading="$resources.createMidTransToken.loading"
							@click="buyCreditsWithMidTrans"
						>
							Buy
						</Button>
					</div>
				</div>
			</div>

			<div>
				<div
					v-if="!paymentGateway"
					class="grid grid-cols-1 gap-2 sm:grid-cols-2"
				>
					<Button
						v-if="
							$account.team.currency === 'INR' || $account.team.razorpay_enabled
						"
						@click="paymentGateway = 'razorpay'"
						class="py-2"
					>
						<img
							class="w-24"
							src="../assets/razorpay.svg"
							alt="Razorpay Logo"
						/>
					</Button>
					<Button @click="paymentGateway = 'stripe'">
						<img
							class="h-7 w-24"
							src="../assets/stripe.svg"
							alt="Stripe Logo"
						/>
					</Button>
					<Button @click="paymentGateway = 'midtrans'">
						<img
							class="h-7 w-24"
							src="../assets/midtrans_logo.svg"
							alt="MidTrans Logo"
						/>
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import BuyPrepaidCredits from './BuyPrepaidCredits.vue';

export default {
	name: 'PrepaidCreditsDialog',
	components: {
		BuyPrepaidCredits
	},
	data() {
		return {
			paymentGateway: null,
			creditsToBuy: 0,
		};
	},
	async mounted() {

		let client_key = await this.$call(
			'optibizpro.utils.get_client_key'
		);
		const razorpayCheckoutJS = document.createElement('script');
		razorpayCheckoutJS.setAttribute(
			'src',
			'https://checkout.razorpay.com/v1/checkout.js'
		);
		razorpayCheckoutJS.async = true;
		document.head.appendChild(razorpayCheckoutJS);

		//get midtrans checkout
		const midtransCheckoutJS = document.createElement('script');
		midtransCheckoutJS.setAttribute(
			'src',
			'https://app.sandbox.midtrans.com/snap/snap.js'
		);
		midtransCheckoutJS.setAttribute(
			'data-client-key',
			client_key
		);
		midtransCheckoutJS.async = true;
		document.head.appendChild(midtransCheckoutJS);

		if (
			this.$account.team.currency === 'USD' &&
			!this.$account.team.razorpay_enabled && !this.$account.team.midtrans_enabled
		) {
			this.paymentGateway = 'stripe';
		}
	},
	props: {
		modelValue: {
			default: true
		},
		minimumAmount: {
			type: Number,
			default: 10
		}
	},
	emits: ['update:modelValue', 'success'],
	resources: {
		createRazorpayOrder() {
			return {
				method: 'press.api.billing.create_razorpay_order',
				params: {
					amount: this.creditsToBuy
				},
				onSuccess(data) {
					this.processOrder(data);
				},
				validate() {
					if (this.creditsToBuy < this.minimumAmount) {
						return 'Amount less than minimum amount required';
					}
				}
			};
		},
		handlePaymentSuccess(response) {
			return {
				method: 'press.api.billing.handle_razorpay_payment_success',
				onSuccess() {
					this.$emit('success');
				}
			};
		},
		handlePaymentFailed() {
			return {
				method: 'press.api.billing.handle_razorpay_payment_failed',
				onSuccess() {
					console.log('Payment Failed.');
				}
			};
		},
		createMidTransToken(){
			return {
				method: 'optibizpro.utils.create_midtrans_token',
				params: {
					amount: this.creditsToBuy
				},
				onSuccess(data) {
					this.processMidTransOrder(data); //this initializes the midtrans snap.js inline checkout
				},
				validate() {
					if (this.creditsToBuy < this.minimumAmount) {
						return 'Amount less than minimum amount required';
					}
				}
			};
		},
		MidTransPaymentSuccess() {
			return {
				method: 'optibizpro.utils.handle_midtrans_payment_success',
				
				onSuccess() {
					this.$emit('success');
				}
			};
		},
		MidTransPaymentFailed() {
			return {
				method: 'optibizpro.utils.handle_midtrans_payment_failed',
				onSuccess() {
					console.log('Payment Failed.');
				}
			};
		},
	},
	methods: {
		buyCreditsWithRazorpay() {
			this.$resources.createRazorpayOrder.submit();
		},
		buyCreditsWithMidTrans(){
			this.$resources.createMidTransToken.submit();
		},
		processMidTransOrder(data){
			var transaction_token = data.token
			window.snap.pay(transaction_token, {
				onSuccess: (result) => {
					/* You may add your own implementation here */
					
					// alert("payment success!");
					result["team"] = this.$account.team.name
					this.$resources.MidTransPaymentSuccess.submit({result});

				},
				onPending: function(result){
					/* You may add your own implementation here */
					alert("awaiting  payment!"); console.log(result);
				},
				onError: function(result){
					/* You may add your own implementation here */
					result["team"] = this.$account.team.name
					this.$resources.MidTransPaymentFailed.submit({result});

					// alert("payment failed!"); console.log(result);
				},
				onClose: function(){
					/* You may add your own implementation here */
					alert('you closed the popup without finishing the payment');
				}
			})
		},
		processOrder(data) {
			const options = {
				key: data.key_id,
				order_id: data.order_id,
				name: 'Frappe Cloud',
				image: '/assets/press/images/frappe-cloud-logo.png',
				prefill: {
					email: this.$account.team.user
				},
				theme: { color: '#2490EF' },
				handler: this.handlePaymentSuccess
			};

			const rzp = new Razorpay(options);

			// Opens the payment checkout frame
			rzp.open();

			// Attach failure handler
			rzp.on('payment.failed', this.handlePaymentFailed);
		},

		handlePaymentSuccess(response) {
			this.$emit('success');
		},

		handlePaymentFailed(response) {
			this.$resources.handlePaymentFailed.submit({ response });
		},

		// MidTransPaymentSuccess_b(response) {
		// 	console.log("respppppppppp",response)
		// 	this.$resources.MidTransPaymentSuccess.submit(response);
		// 	this.$emit('success');
		// },

		// MidTransPaymentFailed(response) {
		// 	this.$resources.MidTransPaymentFailed.submit({ response });
		// }

	},
	watch: {
		minimumAmount(amt) {
			console.log(amt);
		}
	}
};
</script>
