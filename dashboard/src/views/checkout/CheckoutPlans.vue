<template>
	<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
		<div
			v-for="plan in plans"
			class="m-2 flex flex-col justify-between rounded-2xl border border-gray-100 p-4 shadow"
		>
			<div>
				<h4 class="flex justify-between text-xl font-semibold text-gray-900">
					<div>
						<span>
							{{
								currency === 'INR' ? '₹' + plan.price_inr : '$' + plan.price_usd
							}}
							<span class="text-base font-normal text-gray-600">
								{{ plan.block_monthly === 1 ? '/year' : '/mo' }}
							</span>
						</span>
					</div>
				</h4>

				<FeatureList class="my-5" :features="getPlanFeatures(plan)" />
			</div>
			<Button
				variant="subtle"
				class="hover:bg-gray-900 hover:text-white"
				@click="selectPlan(plan)"
			>
				Buy Now
			</Button>
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
		'address',
		'plans'
	],
	resources: {
		sendLoginLink() {
			return {
				url: 'press.api.developer.marketplace.send_login_link',
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
		},
		getPlanFeatures(plan) {
			let features = [
				`${plan.cpu_time_per_day} ` +
					this.$plural(plan.cpu_time_per_day, 'hour', 'hours') +
					' CPU per day',
				this.formatBytes(plan.max_database_usage, 0, 2) + ' Database',
				this.formatBytes(plan.max_storage_usage, 0, 2) + ' Storge'
			];
			if (plan.support_included) {
				features.push('Product warranty + Support');
			}
			return features;
		}
	}
};
</script>
