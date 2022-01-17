<template>
	<div class="space-y-5">
		<AlertSiteActivation :site="site" />
		<AlertSiteUpdate :site="site" />
		<Alert title="Trial" v-if="isInTrial && $account.needsCard">
			Your trial ends {{ trialEndsInDaysText }} after which your site will get
			suspended. Add your billing information to avoid suspension.

			<template #actions>
				<Button class="whitespace-nowrap" route="/welcome" type="primary">
					Add Billing Information
				</Button>
			</template>
		</Alert>
		<Alert title="Trial" v-if="isInTrial && $account.hasBillingInfo">
			Your trial ends {{ trialEndsInDaysText }} after which your site will get
			suspended. Select a plan from the Plan section below to avoid suspension.
		</Alert>
		<Alert title="Attention Required" v-if="limitExceeded">
			Your site has exceeded the allowed usage for your plan. Upgrade your plan
			now.
		</Alert>
		<Alert title="Attention Required" v-else-if="closeToLimits">
			Your site has exceeded 80% of the allowed usage for your plan. Upgrade
			your plan now.
		</Alert>

		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="overview.data">
			<SiteOverviewCPUUsage :site="site" />
			<SiteOverviewRecentActivity
				:site="site"
				:recentActivity="overview.data.recent_activity"
			/>
			<SiteOverviewPlan
				:site="site"
				:plan="overview.data.plan"
				@plan-change="$resources.overview.reload()"
			/>
			<SiteOverviewInfo :site="site" :info="overview.data.info" />
			<SiteOverviewAppSubscriptions class="md:col-span-2" :site="site" />
			<SiteOverviewApps
				:site="site"
				:installedApps="overview.data.installed_apps"
				@app-installed="$resources.overview.reload()"
				@app-uninstalled="$resources.overview.reload()"
			/>
			<SiteOverviewDomains :site="site" />
		</div>
	</div>
</template>

<script>
import AlertSiteActivation from '@/components/AlertSiteActivation.vue';
import AlertSiteUpdate from '@/components/AlertSiteUpdate.vue';
import SiteOverviewCPUUsage from './SiteOverviewCPUUsage.vue';
import SiteOverviewRecentActivity from './SiteOverviewRecentActivity.vue';
import SiteOverviewPlan from './SiteOverviewPlan.vue';
import SiteOverviewInfo from './SiteOverviewInfo.vue';
import SiteOverviewApps from './SiteOverviewApps.vue';
import SiteOverviewDomains from './SiteOverviewDomains.vue';
import SiteOverviewAppSubscriptions from './SiteOverviewAppSubscriptions.vue';

import { DateTime } from 'luxon';

export default {
	name: 'SiteOverview',
	props: ['site'],
	components: {
		AlertSiteActivation,
		AlertSiteUpdate,
		SiteOverviewCPUUsage,
		SiteOverviewRecentActivity,
		SiteOverviewPlan,
		SiteOverviewInfo,
		SiteOverviewApps,
		SiteOverviewDomains,
		SiteOverviewAppSubscriptions
	},
	resources: {
		overview() {
			return {
				method: 'press.api.site.overview',
				params: { name: this.site.name },
				keepData: true,
				auto: true
			};
		}
	},
	computed: {
		closeToLimits() {
			if (!(this.site && this.$resources.overview.data)) return false;
			let usage = this.$resources.overview.data.plan.usage_in_percent;
			return [usage.cpu, usage.database, usage.disk].some(
				x => 100 >= x && x > 80
			);
		},
		limitExceeded() {
			if (!(this.site && this.$resources.overview.data)) return false;
			let usage = this.$resources.overview.data.plan.usage_in_percent;
			return [usage.cpu, usage.database, usage.disk].some(x => x > 100);
		},
		isInTrial() {
			return this.site?.trial_end_date;
		},
		trialEndsInDaysText() {
			if (!this.site?.trial_end_date) {
				return 0;
			}
			let diff = this.$date(this.site.trial_end_date)
				.diff(DateTime.local(), ['days'])
				.toObject();

			let days = diff.days;
			if (days > 1) {
				return `in ${Math.floor(days)} days`;
			}
			return 'in a day';
		}
	}
};
</script>
