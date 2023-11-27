<template>
	<ConfigEdit
		v-if="bench && !bench?.public"
		:configData="benchConfig"
		:updateConfigMethod="updateBenchConfigMethod"
	/>
</template>

<script>
// TODO: change below file's name to ConfigEditor.vue after dashboard migration
import ConfigEdit from '../ConfigEdit.vue';

export default {
	name: 'BenchConfig',
	components: {
		ConfigEdit
	},
	props: ['bench'],
	data() {
		return {
			editMode: false,
			isCommonSiteConfigFormDirty: false,
			isBenchConfigFormDirty: false
		};
	},
	methods: {
		benchConfig() {
			return {
				url: 'press.api.bench.bench_config',
				params: {
					name: this.bench?.name
				},
				auto: true,
				initialData: []
			};
		},
		updateBenchConfigMethod(updatedConfig) {
			return {
				url: 'press.api.bench.update_config',
				params: {
					name: this.bench?.name,
					config: JSON.stringify(updatedConfig)
				}
			};
		}
	}
};
</script>
