<script setup>
import { computed, ref, reactive } from 'vue';
import useResource from '@/composables/resource.js';
import SiteOverviewRecentActivity from '../SiteOverviewRecentActivity.vue';
import SiteOverviewInfo from '../SiteOverviewInfo.vue';
import call from '../../controllers/call.js';

const props = defineProps({ subData: Object });
</script>

<template>
	<div 
		class="grid grid-cols-1 gap-5 sm:grid-cols-2"
		v-if="subData">
		<SiteOverviewInfo :site="subData.site" :info="subData.site_overview.info" />
		<SiteOverviewRecentActivity
			:site="subData.subscription.site"
			:recentActivity="subData.site_overview.recent_activity"
		/>
	</div>
</template>
