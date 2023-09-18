<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
		<Tags
			v-if="bench"
			:name="bench.name"
			doctype="Release Group"
			:resourceTags="bench.bench_tags"
			:tags="bench.tags"
		/>
		<BenchOverviewRegions :bench="bench" />
		<BenchDependencies :bench="bench" />
	</div>
</template>

<script>
import Tags from '@/components/Tags.vue';
import BenchOverviewRegions from './BenchOverviewRegions.vue';
import BenchDependencies from './BenchDependencies.vue';

export default {
	name: 'BenchSettings',
	props: ['bench'],
	components: {
		Tags,
		BenchDependencies,
		BenchOverviewRegions
	}
};
</script>
