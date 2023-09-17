<template>
	<div class="space-y-6" v-if="bench && !bench?.public">
		<ConfigEditor
			title="Bench Config"
			subtitle="Add and update key value pairs to your bench's common_site_config.json and bench_config.json"
			:configData="benchConfig"
			:updateConfigMethod="updateBenchConfigMethod"
		/>
		<ConfigEditor
			title="Dependencies"
			subtitle="Update dependencies for your bench"
			:configData="dependencies"
			:updateConfigMethod="updateDependencies"
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
		},
		dependencies() {
			return {
				method: 'press.api.bench.dependencies',
				params: {
					name: this.bench?.name
				},
				auto: true,
				default: []
			};
		},
		updateDependencies(updatedConfig) {
			return {
				method: 'press.api.bench.update_dependencies',
				params: {
					name: this.bench?.name,
					dependencies: JSON.stringify(updatedConfig)
				}
			};
		}
	}
};
</script>
