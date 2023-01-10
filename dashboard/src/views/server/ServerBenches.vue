<template>
	<BenchList 
		v-if="$resources.benches.data"
		:benches="$resources.benches.data"
	></BenchList>
</template>
<script>

import BenchList from '../bench/BenchList.vue';
export default {
	name: 'ServerBenches',
	components: {BenchList},
	props: ['server'],
	resources: {
		benches() {
			return {
				method: 'press.api.server.groups',
				params: {
					name: this.server?.name
				},
				auto: true
			};
		},
	},
};
</script>
