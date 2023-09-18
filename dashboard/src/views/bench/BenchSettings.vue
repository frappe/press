<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
		<Tags
			v-if="bench"
			:name="benchName"
			doctype="Release Group"
			:resourceTags="bench.bench_tags"
			:tags="bench.tags"
		/>
		<BenchOverviewRegions :benchName="benchName" />
		<BenchDependencies :benchName="benchName" />
	</div>
</template>

<script>
import Tags from '@/components/Tags.vue';
import BenchOverviewRegions from './BenchOverviewRegions.vue';
import BenchDependencies from './BenchDependencies.vue';

export default {
	name: 'BenchSettings',
	props: ['bench', 'benchName'],
	components: {
		Tags,
		BenchDependencies,
		BenchOverviewRegions
	}
};
</script>
