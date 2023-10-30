<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
		<Tags
			v-if="bench"
			:name="benchName"
			doctype="Release Group"
			:resourceTags="bench.bench_tags"
			:tags="bench.tags"
		/>
		<BenchRegions :benchName="benchName" />
		<BenchDependencies :benchName="benchName" />
	</div>
</template>

<script>
import Tags from '@/components/Tags.vue';
import BenchRegions from './BenchRegions.vue';
import BenchDependencies from './BenchDependencies.vue';

export default {
	name: 'BenchSettings',
	props: ['bench', 'benchName'],
	components: {
		Tags,
		BenchDependencies,
		BenchRegions
	}
};
</script>
