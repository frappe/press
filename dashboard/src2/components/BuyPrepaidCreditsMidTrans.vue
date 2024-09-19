<template>
	<div>
		<p v-if="$team.doc.currency === 'INR'" class="mt-3 text-p-sm">
			If you select Razorpay, you can pay using Credit Card, Debit Card, Net
			Banking, UPI, Wallets, etc. If you are using Net Banking, it may take upto
			5 days for balance to reflect.
		</p>
		<ErrorMessage
			class="mt-3"
			:message="$resources.createMidTransToken.error"
		/>
		<div class="mt-4 flex w-full justify-between">
			<div></div>
			<Button
				variant="solid"
				:loading="$resources.createMidTransToken.loading"
				v-if="!isPaymentComplete"
				@click="buyCreditsWithMidTrans"
			>
				Proceed to payment using Midtrans
			</Button>
			<Button v-else variant="solid" :loading="isVerifyingPayment"
				>Confirming payment</Button
			>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../utils/error';

export default {
	name: 'BuyPrepaidCreditsMidTrans',
	// components: {
	// 	BuyPrepaidCredits
	// },
	data() {
		return {
			paymentGateway: null,
			creditsToBuy: 0,
			isPaymentComplete: false,
 			isVerifyingPayment: false
		};
	},
	async mounted() {
		//let client_key = await this.$resources.client_key.promise;
		let client_key = await this.$resources.client_key.submit()
		
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
			this.$team.doc.currency === 'USD' &&
			!this.$team.doc.razorpay_enabled && !this.$team.doc.midtrans_enabled
		) {
			this.paymentGateway = null; //default to null not stripe
		}
	},
    props: {
		amount: {
			default: 0
		},
		minimumAmount: {
			default: 10
		},
		isOnboarding: {
			default: false
		}
	},
	
	
	emits: ['update:modelValue', 'success'],
	resources: {
		
		client_key() {
			return {
				url: 'optibizpro.utils.get_client_key',
				async onSuccess(data) {
					// console.log(data)
					//this.client_key = data["message"]
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
		// handlePaymentFailed() {
		// 	return {
		// 		method: 'press.api.billing.handle_razorpay_payment_failed',
		// 		onSuccess() {
		// 			console.log('Payment Failed.');
		// 		}
		// 	};
		// },
		
		createMidTransToken() {
			return {
				url: 'optibizpro.utils.create_midtrans_token',
				params: {
					amount: this.amount,
					customer_name : this.$team.doc.team_title,
					customer_email : this.$team.doc.user
				},
				onSuccess(data) {
					this.processMidTransOrder(data); //this initializes the midtrans snap.js inline checkout
				},
				validate() {
					if (this.amount < this.minimumAmount) {
						return 'Amount less than minimum amount required';
					}
				},
				error () {

				},
				loading () {

				}
			};
		},
		MidTransPaymentSuccess() {
			return {
				url: 'optibizpro.utils.handle_midtrans_payment_success',
				
				onSuccess() {
					this.$emit('success');
				}
			};
		},
		MidTransPaymentSuccessTest() {
			return {
				url: 'optibizpro.utils.create_midtrans_token',
				params: {
					amount: 0,//this.creditsToBuy,
					customer_name : "dj" ,//this.$account.user.full_name,
					customer_email : "jdj",//this.$account.user.email
				},
				onSuccess() {
					this.$emit('success');
				}
			};
			// return {
				
			// 	url: 'optibizpro.utils.create_midtrans_token',
			// 	params: {
			// 		amount: this.creditsToBuy,
			// 		customer_name : this.$account.user.full_name,
			// 		customer_email : this.$account.user.email
			// 	},
			// 	onSuccess(data) {
			// 		this.processMidTransOrder(data); //this initializes the midtrans snap.js inline checkout
			// 	},
				
			// 	error () {

			// 	},
			// 	loading () {
					
			// 	}
			// };
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
					result["team"] = this.$team.doc.name
					result["user"] = this.$team.doc.user.full_name
					result["email"] = this.$team.doc.user.email
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
