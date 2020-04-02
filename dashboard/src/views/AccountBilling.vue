<template>
	<div>
		<div class="text-gray-800" v-if="state === 'Fetching'">
			Fetching billing information..
		</div>
		<section v-if="state.startsWith('ShowSetup')">
			<h2 class="text-lg font-medium">Setup Payment Method</h2>
			<p class="text-gray-600">
				Add your card details to start your subscription
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div class="px-6 py-4">
					<Button
						type="primary"
						@click="state = 'ShowSetup.ShowStripeCard'"
						v-if="state != 'ShowSetup.ShowStripeCard'"
					>
						Setup Payment Method
					</Button>
					<StripeCard
						v-if="state === 'ShowSetup.ShowStripeCard'"
						@complete="onCardAdd"
					/>
				</div>
			</div>
		</section>
		<section v-if="state === 'ShowPaymentMethods'">
			<h2 class="text-lg font-medium">Payment Methods</h2>
			<p class="text-gray-600">
				Cards you have added for automatic billing
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded-md shadow sm:w-1/2"
			>
				<div
					class="grid items-center grid-cols-3 px-6 py-4 hover:bg-gray-50"
					v-for="paymentMethod in paymentMethods"
					:key="paymentMethod.id"
				>
					<div class="font-semibold">•••• {{ paymentMethod.card.last4 }}</div>
					<div>
						{{ paymentMethod.billing_details.name }}
					</div>
					<div>
						{{ paymentMethod.card.exp_month }} /
						{{ paymentMethod.card.exp_year }}
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
export default {
	name: 'AccountBilling',
	components: {
		StripeCard
	},
	data() {
		return {
			state: 'Idle',
			paymentMethods: null
		};
	},
	mounted() {
		this.state = 'Fetching';
		this.fetchPaymentMethods();
	},
	methods: {
		async fetchPaymentMethods() {
			this.paymentMethods = await this.$call(
				'press.api.billing.get_payment_methods'
			);
			if (this.paymentMethods.length > 0) {
				this.state = 'ShowPaymentMethods';
			} else {
				this.state = 'ShowSetup';
			}
		},
		onCardAdd() {
			this.state = 'Idle';
			this.fetchPaymentMethods();
			this.$call('press.api.billing.after_card_add');
		}
	}
};
</script>
