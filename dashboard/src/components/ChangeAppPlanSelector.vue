<template>
	<div>
		<ErrorMessage :error="$resources.getAppPlans.error" />

		<Button
			v-if="
				$resources.getAppPlans.loading ||
				$resources.getMarketplaceAppInfo.loading
			"
			:loading="true"
			loadingText="Loading Plans..."
		></Button>

		<div v-if="plans && appInfo" class="mb-6 flex flex-row items-center">
			<Avatar
				class="mr-2"
				size="lg"
				shape="square"
				:imageURL="appInfo.image"
				:label="appInfo.title"
			/>

			<div class="flex flex-col">
				<h4 class="text-xl font-semibold text-gray-900">{{ appInfo.title }}</h4>
				<p class="text-base text-gray-600">Choose your plans</p>
			</div>
		</div>

		<div v-if="plans" class="mx-auto grid grid-cols-1 gap-2 md:grid-cols-3">
			<AppPlanCard
				v-for="plan in plans"
				:plan="plan"
				:key="plan.name"
				:selected="selectedPlan == plan"
				@click.native="handleCardClick(plan)"
			/>
		</div>
	</div>
</template>

<script>
import AppPlanCard from '@/components/AppPlanCard.vue';

export default {
	name: 'ChangeAppPlanCards',
	components: {
		AppPlanCard
	},
	props: ['app', 'group', 'frappeVersion', 'currentPlan'],
	emits: ['change'],
	data() {
		return {
			selectedPlan: null
		};
	},
	resources: {
		getAppPlans() {
			return {
				method: 'press.api.marketplace.get_app_plans',
				params: {
					app: this.app,
					release_group: this.group,
					frappe_version: this.frappeVersion
				},
				onSuccess(plans) {
					if (this.currentPlan) {
						for (let plan of plans) {
							if (plan.name === this.currentPlan) {
								this.selectedPlan = plan;
								break;
							}
						}
					}
				},
				auto: true
			};
		},
		getMarketplaceAppInfo() {
			return {
				method: 'press.api.marketplace.get_app_info',
				params: {
					app: this.app
				},
				auto: true
			};
		}
	},
	methods: {
		handleCardClick(plan) {
			this.selectedPlan = plan;
			this.$emit('change', plan);
		}
	},
	computed: {
		plans() {
			if (
				this.$resources.getAppPlans.data &&
				!this.$resources.getAppPlans.loading
			) {
				return this.$resources.getAppPlans.data;
			}
		},
		appInfo() {
			if (
				!this.$resources.getMarketplaceAppInfo.loading &&
				this.$resources.getMarketplaceAppInfo.data
			) {
				return this.$resources.getMarketplaceAppInfo.data;
			}
		}
	}
};
</script>
