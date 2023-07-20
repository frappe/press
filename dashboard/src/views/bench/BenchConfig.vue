<template>
	<div class="space-y-10" v-if="bench">
		<Card
			title="Common Site Config"
			subtitle="Add and update key value pairs to your bench's common_site_config.json"
		>
			<template #actions>
				<Button icon-left="edit" v-if="!editMode" @click="editMode = true">
					Edit Config
				</Button>
				<Button
					v-if="editMode"
					:loading="$resources.benchConfig.loading"
					@click="
						() => {
							$resources.benchConfig.reload().then(() => {
								editMode = false;
								isCommonSiteConfigFormDirty = false;
								isBenchConfigFormDirty = false;
							});
						}
					"
				>
					Discard changes
				</Button>
				<Button
					appearance="primary"
					v-if="editMode"
					@click="updateBenchConfig"
					:loading="$resources.updateBenchConfig.loading"
				>
					Save changes
				</Button>
			</template>
			<ConfigEditor
				:configData="$resources.benchConfig.data.common_site_config"
				:standardConfigKeys="$resources.standardConfigKeys.data"
				:editMode="editMode"
				@isDirty="val => (isCommonSiteConfigFormDirty = val)"
			/>
			<ConfigEditor
				class="mt-4"
				title="Bench Config"
				subtitle="Add and update key value pairs to your bench's bench_config.json"
				:configData="$resources.benchConfig.data.bench_config"
				:standardConfigKeys="$resources.standardConfigKeys.data"
				:customAddConfig="customAddConfig"
				:editMode="editMode"
				:maxNoOfConfigs="1"
				@isDirty="val => (isBenchConfigFormDirty = val)"
			/>
		</Card>
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
	resources: {
		benchConfig() {
			return {
				method: 'press.api.bench.bench_config',
				params: {
					release_group_name: this.bench?.name
				},
				auto: true,
				default: {
					common_site_config: [],
					bench_config: []
				}
			};
		},
		standardConfigKeys: 'press.api.config.standard_keys',
		updateBenchConfig() {
			const commonSiteConfig =
				this.$resources.benchConfig.data.common_site_config;
			const benchConfig = this.$resources.benchConfig.data.bench_config;

			const updatedCommonSiteConfig = commonSiteConfig.map(d => {
				let value = d.value;
				if (d.type === 'Number') {
					value = Number(d.value);
				} else if (d.type == 'JSON') {
					try {
						value = JSON.parse(d.value || '{}');
					} catch (error) {}
				}
				return {
					key: d.key,
					value,
					type: d.type
				};
			});

			const updatedBenchConfig = benchConfig.map(d => {
				return d.key === 'http_timeout'
					? {
							key: d.key,
							value: d.value,
							type: 'Number'
					  }
					: {};
			});

			return {
				method: 'press.api.bench.update_config',
				params: {
					name: this.bench?.name,
					common_site_config: JSON.stringify(updatedCommonSiteConfig),
					bench_config: JSON.stringify(updatedBenchConfig)
				},
				async validate() {
					let keys = updatedCommonSiteConfig.map(d => d.key);
					if (keys.length !== [...new Set(keys)].length) {
						return 'Duplicate key';
					}
					let invalidKeys = await this.$call('press.api.config.is_valid', {
						keys: JSON.stringify(keys)
					});
					if (invalidKeys?.length > 0) {
						return `Invalid key: ${invalidKeys.join(', ')}`;
					}
					for (let config of updatedCommonSiteConfig) {
						if (config.type === 'JSON') {
							try {
								JSON.parse(JSON.stringify(config.value));
							} catch (error) {
								return `Invalid JSON -- ${error}`;
							}
						} else if (config.type === 'Number') {
							try {
								Number(config.value);
							} catch (error) {
								return 'Invalid Number';
							}
						}
					}

					for (let config of updatedBenchConfig) {
						if (config === {}) continue;
						if (isNaN(config.value)) return 'Value is not a number';
					}
				},
				onSuccess() {
					this.editMode = false;
					this.isCommonSiteConfigFormDirty = false;
					this.isBenchConfigFormDirty = false;
				}
			};
		}
	},
	methods: {
		customAddConfig() {
			return {
				key: 'http_timeout',
				value: '',
				type: 'Number'
			};
		},
		updateBenchConfig() {
			if (this.isCommonSiteConfigFormDirty || this.isBenchConfigFormDirty) {
				this.$resources.updateBenchConfig.submit();
			} else {
				this.editMode = false;
				this.isCommonSiteConfigFormDirty = false;
				this.isBenchConfigFormDirty = false;
			}
		}
	}
};
</script>
