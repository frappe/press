<template>
	<div class="space-y-6" v-if="bench && !bench?.public">
		<ConfigEditor
			title="Bench Config"
			subtitle="Add and update key value pairs to your bench's common_site_config.json and bench_config.json"
			:configData="benchConfig"
			:updateConfigMethod="updateBenchConfigMethod"
		/>
	</div>
</template>

<script>
import ConfigEditor from '@/components/ConfigEditor.vue';

export default {
	name: 'BenchConfig',
	components: {
		ConfigEditor
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
				method: 'press.api.bench.bench_config',
				params: {
					release_group_name: this.bench?.name
				},
				auto: true,
				default: []
			};
		},
		updateBenchConfigMethod(updatedConfig) {
			return {
				method: 'press.api.bench.update_config',
				params: {
					name: this.bench?.name,
					config: JSON.stringify(updatedConfig)
				}
			};
		}
	}
};
</script>
