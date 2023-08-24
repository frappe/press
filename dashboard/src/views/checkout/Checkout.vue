<template>
	<div class="p-0" v-if="$resources.subscriptions.data">
		<ErrorMessage :message="errorMessage" />
		<Apps
			v-if="step === 1"
			:data="$resources.subscriptions.data"
			v-model:selectedSubscription="selectedSubscription"
			v-model:step="step"
		/>
		<Plans
			v-if="step === 2"
			:selectedSubscription="selectedSubscription"
			:secretKey="secretKey"
			:address="$resources.subscriptions.data.address"
			:currency="$resources.subscriptions.data.currency"
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
		<ConfirmEmail
			v-if="step === 5"
			:email="$resources.subscriptions.data.team"
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
	data() {
		return {
			secretKey: null,
			subscriptions: [],
			selectedSubscription: '',
			selectedPlan: '',
			step: 1,
			errorMessage: null
		};
	},
	created() {
		const params = new URLSearchParams(window.location.search);
		this.secretKey = params.get('secret_key');

		if (this.secretKey != null) {
			this.$resources.subscriptions.submit();
		}
	},
	resources: {
		subscriptions() {
			return {
				method: 'press.api.developer.marketplace.get_subscriptions',
				params: {
					secret_key: this.secretKey
				},
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
