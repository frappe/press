<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
		<Tags
			:name="bench.name"
			doctype="Release Group"
			:resourceTags="bench.bench_tags"
			:tags="bench.tags"
		/>
	</div>
</template>

<script>
import Tags from '@/components/Tags.vue';

export default {
	name: 'BenchSettings',
	props: ['bench'],
	components: {
		Tags
	}
};
</script>
