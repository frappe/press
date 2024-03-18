<template>
	<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
		<div
			v-for="plan in subscription.plans"
			class="m-2 flex flex-col justify-between rounded-2xl border border-gray-100 p-4 shadow"
		>
			<div>
				<h4 class="flex justify-between text-xl font-semibold text-gray-900">
					<div>
						<span>
							{{
								subscription.currency === 'INR'
									? '₹' + plan.price_inr
									: '$' + plan.price_usd
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
				:disabled="subscription.current_plan === plan.name"
				:class="{
					'hover:bg-gray-900 hover:text-white':
						subscription.current_plan != plan.name
				}"
				@click="selectPlan(plan)"
				:loading="$resources.changeSitePlan.loading"
			>
				{{
					subscription.current_plan === plan.name ? 'Current Plan' : 'Buy Now'
				}}
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
		'selectedPlan',
		'currency',
		'step',
		'secretKey',
		'subscription',
		'team'
	],
	resources: {
		changeSitePlan() {
			return {
				url: 'press.api.developer.marketplace.change_site_plan'
			};
		}
	},
	methods: {
		selectPlan(plan) {
			this.$emit('update:selectedPlan', plan);
			this.capturePosthogEvent();

			if (Object.keys(this.subscription.address).length > 0) {
				if (this.subscription.has_billing_info) {
					this.$resources.changeSitePlan.submit({
						secret_key: this.secretKey,
						plan: plan.name
					});
					this.$emit('update:step', 4);
				} else {
					this.$emit('update:step', 3);
				}
			} else {
				this.$emit('update:step', 2);
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
		},
		capturePosthogEvent() {
			if (window.posthog) {
				posthog.capture('fc_subscribe_plan_selected', {
					distinct_id: this.team
				});
			}
		}
	}
};
</script>
