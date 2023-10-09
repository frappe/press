<template>
	<div class="p-0" v-if="$resources.subscriptions.data">
		<ErrorMessage :message="errorMessage" />
		<Plans
			v-if="step === 1"
			:selectedSubscription="selectedSubscription"
			:secretKey="secretKey"
			:address="$resources.subscriptions.data.address"
			:currency="$resources.subscriptions.data.currency"
			:plans="$resources.subscriptions.data.plans"
			v-model:step="step"
			v-model:selectedPlan="selectedPlan"
		/>
		<Address
			v-if="step === 3"
			:secretKey="secretKey"
			:currency="$resources.subscriptions.data.currency"
			:countries="$resources.subscriptions.data.countries"
			v-model:step="step"
		/>
		<Payment
			v-if="step === 4"
			:selectedSubscription="selectedSubscription"
			:selectedPlan="selectedPlan"
			:plan="selectedPlan"
			:currency="$resources.subscriptions.data.currency"
			:secretKey="secretKey"
			v-model:step="step"
		/>
	</div>
</template>

<script>
import Apps from './CheckoutApps.vue';
import Plans from './CheckoutPlans.vue';
import Address from './CheckoutAddress.vue';
import Payment from './CheckoutPayment.vue';
import ConfirmEmail from './CheckoutConfirmEmail.vue';

export default {
	name: 'Checkout',
	components: {
		Apps,
		Plans,
		Address,
		Payment,
		ConfirmEmail
	},
	props: ['secretKey'],
	data() {
		return {
			subscriptions: [],
			selectedSubscription: '',
			selectedPlan: '',
			step: 1,
			errorMessage: null
		};
	},
	resources: {
		subscriptions() {
			return {
				url: 'press.api.developer.marketplace.get_subscription',
				params: {
					secret_key: this.secretKey
				},
				auto: true,
				onSuccess(r) {
					this.errorMessage = null;
				},
				onError(e) {
					this.errorMessage = e;
				}
			};
		}
	}
};
</script>
