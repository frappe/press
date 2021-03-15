<template>
	<div class="space-y-5">
		<AlertSiteActivation :site="site" />
		<AlertSiteUpdate :site="site" />
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
import AlertSiteActivation from '@/components/AlertSiteActivation';
import AlertSiteUpdate from '@/components/AlertSiteUpdate';
import SiteOverviewCPUUsage from './SiteOverviewCPUUsage';
import SiteOverviewRecentActivity from './SiteOverviewRecentActivity.vue';
import SiteOverviewPlan from './SiteOverviewPlan.vue';
import SiteOverviewInfo from './SiteOverviewInfo.vue';
import SiteOverviewApps from './SiteOverviewApps.vue';
import SiteOverviewDomains from './SiteOverviewDomains.vue';

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
		SiteOverviewDomains
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
		}
	}
};
</script>
