<template>
	<div
		class="text-sm cursor-pointer w-fit mb-8"
		v-on:click="$emit('update:step', 1)"
	>
		← Back to Apps
	</div>
	<div class="flex justify-between mb-4 p-4 rounded-lg border text-base">
		<span class="self-center"
			>Checkout Frappe Cloud plans for site hosting from
			<span class="font-bold"
				>{{ currency === 'INR' ? '₹ 820' : '$ 10' }} Onwards</span
			>
		</span>
		<Button
			appearance="secondary"
			@click="$resources.sendLoginLink.submit()"
			:loading="$resources.sendLoginLink.loading"
		>
			Get Login Link
		</Button>
	</div>
	<div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
		<div
			v-for="plan in $resources.plans.data"
			class="m-2 flex flex-col justify-between rounded-2xl border border-gray-100 p-4 shadow"
		>
			<h4 class="flex justify-between text-xl font-semibold text-gray-900">
				<div>
					<span v-if="plan.is_free"> Free </span>
					<span v-else>
						{{
							currency === 'INR' ? '₹' + plan.price_inr : '$' + plan.price_usd
						}}
						<span class="text-base font-normal text-gray-600">
							{{ plan.block_monthly === 1 ? '/year' : '/mo' }}
						</span>
					</span>
				</div>
			</h4>

			<FeatureList class="my-5" :features="plan.features" />
			<Button appearance="primary" @click="selectPlan(plan)"> Buy Now </Button>
		</div>
	</div>
</template>

<script>
import FeatureList from '@/components/FeatureList.vue';

export default {
	name: 'Apps',
	components: {
		FeatureList
	},
	emits: ['update:selectedPlan', 'update:step'],
	props: [
		'selectedSubscription',
		'selectedPlan',
		'currency',
		'step',
		'secretKey',
		'address'
	],
	resources: {
		plans() {
			return {
				method: 'press.api.developer.marketplace.get_plans',
				params: {
					secret_key: this.secretKey,
					subscription: this.selectedSubscription.name
				},
				auto: true
			};
		},
		sendLoginLink() {
			return {
				method: 'press.api.developer.marketplace.send_login_link',
				params: {
					secret_key: this.secretKey
				},
				onSuccess() {
					this.$emit('update:step', 5);
				}
			};
		}
	},
	methods: {
		selectPlan(plan) {
			this.$emit('update:selectedPlan', plan);

			if (this.address) {
				this.$emit('update:step', 4);
			} else {
				this.$emit('update:step', 3);
			}
		}
	}
};
</script>
