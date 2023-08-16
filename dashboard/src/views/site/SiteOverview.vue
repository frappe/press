<script setup>
import { createResource } from 'frappe-ui';
import SiteOverviewPlan from './SiteOverviewPlan.vue';
import SiteOverviewInfo from './SiteOverviewInfo.vue';
import SiteOverviewDomains from './SiteOverviewDomains.vue';
import SiteOverviewCPUUsage from './SiteOverviewCPUUsage.vue';
import SiteActivity from './SiteActivity.vue';

const props = defineProps({ site: Object });

const overview = createResource({
	url: 'press.api.site.overview',
	params: { name: props.site?.name },
	auto: true
});
</script>

<template>
	<div class="space-y-5" v-if="site">
		<div
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
			v-if="site && overview.data"
		>
			<SiteOverviewCPUUsage :site="site" />
			<SiteOverviewPlan
				:site="site"
				:plan="overview.data.plan"
				@plan-change="overview.reload()"
			/>
			<SiteOverviewInfo :site="site" :info="overview.data.info" />
			<SiteOverviewDomains :site="site" />
			<SiteActivity :site="site" />
		</div>
	</div>
</template>
