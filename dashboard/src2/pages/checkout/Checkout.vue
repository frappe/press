<template>
	<div class="p-0" v-if="$resources.subscription.data">
		<ErrorMessage :message="errorMessage" />
		<Plans
			v-if="step === 1"
			:secretKey="secretKey"
			:subscription="$resources.subscription.data"
			:team="$resources.subscription.data.team"
			v-model:step="step"
			v-model:selectedPlan="selectedPlan"
		/>
		<Address
			v-if="step === 2"
			:secretKey="secretKey"
			:currency="$resources.subscription.data.currency"
			:countries="$resources.subscription.data.countries"
			v-model:step="step"
			v-model:newAddress="newAddress"
		/>
		<Payment
			v-if="step === 3"
			:selectedPlan="selectedPlan"
			:currency="$resources.subscription.data.currency"
			:withoutAddress="true"
			:address="
				Object.keys($resources.subscription.data.address).length > 0
					? $resources.subscription.data.address
					: newAddress
			"
			:secretKey="secretKey"
			v-model:step="step"
		/>
		<PlanChangeSuccessful
			v-if="step === 4"
			:selectedPlan="selectedPlan.name"
			:currentPlan="$resources.subscription.data.current_plan"
			v-model:step="step"
		/>
	</div>
</template>

<script>
import Apps from './CheckoutApps.vue';
import Plans from './CheckoutPlans.vue';
import Address from './CheckoutAddress.vue';
import Payment from './CheckoutPayment.vue';
import PlanChangeSuccessful from './PlanChangeSuccessful.vue';

export default {
	name: 'Checkout',
	components: {
		Apps,
		Plans,
		Address,
		Payment,
		PlanChangeSuccessful
	},
	props: ['secretKey'],
	data() {
		return {
			selectedSubscription: '',
			selectedPlan: '',
			step: 1,
			newAddress: {},
			errorMessage: null
		};
	},
	resources: {
		subscription() {
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
