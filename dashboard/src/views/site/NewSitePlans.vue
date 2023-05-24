<template>
	<div>
		<label class="text-lg font-semibold"> Choose your plan </label>
		<p class="text-base text-gray-700">
			Select a plan based on the type of usage you are expecting on your site.
		</p>
		<AlertBillingInformation class="mt-4" />
		<div class="mt-4">
			<div v-if="$resources.plans.loading" class="flex justify-center">
				<LoadingText />
			</div>
			<SitePlansTable
				v-if="plans"
				:plans="plans"
				:selectedPlan="selectedPlan"
				@update:selectedPlan="plan => $emit('update:selectedPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import { DateTime } from 'luxon';
import SitePlansTable from '@/components/SitePlansTable.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'Plans',
	emits: ['update:selectedPlan'],
	props: ['selectedPlan', 'benchCreation', 'benchTeam'],
	components: {
		SitePlansTable,
		AlertBillingInformation
	},
	data() {
		return {
			plans: null
		};
	},
	resources: {
		plans() {
			return {
				method: 'press.api.site.get_plans',
				auto: true,
				onSuccess(r) {
					this.plans = r.map(plan => {
						plan.disabled = !this.$account.hasBillingInfo;
						return plan;
					});

					// poor man's bench paywall
					// this will disable creation of $10 sites on private benches
					// wanted to avoid adding a new field, so doing this with a date check :)
					let benchCreation = DateTime.fromSQL(this.benchCreation);
					let paywalledBenchDate = DateTime.fromSQL('2021-09-21 00:00:00');
					let isPaywalledBench = benchCreation > paywalledBenchDate;
					if (
						isPaywalledBench &&
						this.$account.user.user_type != 'System User'
					) {
						this.plans = this.plans.filter(plan => plan.price_usd >= 25);
					}
				}
			};
		}
	}
};
</script>
