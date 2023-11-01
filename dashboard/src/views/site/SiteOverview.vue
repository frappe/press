<script setup>
import SiteOverviewPlan from './SiteOverviewPlan.vue';
import SiteOverviewInfo from './SiteOverviewInfo.vue';
import SiteOverviewDomains from './SiteOverviewDomains.vue';
import SiteOverviewCPUUsage from './SiteOverviewCPUUsage.vue';
import SiteActivity from './SiteActivity.vue';

const props = defineProps({ site: Object, plan: Object });
</script>

<template>
	<div class="space-y-5" v-if="site">
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="site">
			<SiteOverviewCPUUsage :site="site" />
			<SiteOverviewPlan
				:site="site"
				:plan="plan"
				@plan-change="$emit('plan-change')"
			/>
			<SiteOverviewInfo :site="site" :info="site.info" />
			<SiteOverviewDomains :site="site" />
			<SiteActivity :site="site" />
		</div>
	</div>
</template>
