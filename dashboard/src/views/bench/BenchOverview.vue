<template>
	<div class="space-y-5" v-if="bench">
		<AlertBenchUpdate v-if="bench.no_sites <= 0" :bench="bench" />
		<AlertUpdate v-else :bench="bench" />
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<BenchOverviewInfo :bench="bench" />
			<BenchOverviewVersions :bench="bench" />
			<BenchOverviewRecentDeploys :bench="bench" />
			<BenchOverviewRegions :bench="bench" />
		</div>
	</div>
</template>

<script>
import AlertUpdate from '@/components/AlertUpdate.vue';
import AlertBenchUpdate from '@/components/AlertBenchUpdate.vue';
import BenchOverviewInfo from './BenchOverviewInfo.vue';
import BenchOverviewRecentDeploys from './BenchOverviewRecentDeploys.vue';
import BenchOverviewVersions from './BenchOverviewVersions.vue';
import BenchOverviewRegions from './BenchOverviewRegions.vue';

export default {
	name: 'BenchGeneral',
	props: ['bench'],
	components: {
		AlertUpdate,
		AlertBenchUpdate,
		BenchOverviewInfo,
		BenchOverviewRecentDeploys,
		BenchOverviewVersions,
		BenchOverviewRegions
	}
};
</script>
