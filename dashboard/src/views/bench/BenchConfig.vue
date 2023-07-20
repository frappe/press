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
			<div class="flex space-x-4">
				<div class="w-full shrink-0 space-y-4 md:w-2/3">
					<div class="space-y-4" v-if="editMode">
						<div
							class="grid grid-cols-5 gap-4"
							v-for="(config, i) in $resources.benchConfig.data
								.common_site_config"
							:key="i"
						>
							<Input
								type="text"
								placeholder="key"
								v-model="config.key"
								class="col-span-2"
								@change="isCommonSiteConfigFormDirty = true"
							/>
							<Input
								type="select"
								placeholder="type"
								v-model="config.type"
								:options="['String', 'Number', 'JSON', 'Boolean']"
								@change="onTypeChange(config)"
							/>
							<div class="col-span-2 flex items-center">
								<Input
									class="w-full"
									v-bind="configInputProps(config)"
									:input-class="{ 'font-mono': config.type === 'JSON' }"
									placeholder="value"
									v-model="config.value"
									@change="isCommonSiteConfigFormDirty = true"
								/>
								<button
									class="ml-2 rounded-md p-1 hover:bg-gray-100"
									@click="removeCommonSiteConfig(config)"
								>
									<FeatherIcon name="x" class="h-5 w-5 text-gray-700" />
								</button>
							</div>
						</div>
						<ErrorMessage :message="$resources.benchConfig.error" />
						<Button @click="addCommonSiteConfig" v-if="editMode">
							Add Key
						</Button>
					</div>
					<div v-else>
						<Form
							v-if="
								readOnlyFormPropsForCommonSiteConfig.fields &&
								readOnlyFormPropsForCommonSiteConfig.fields.length
							"
							v-bind="readOnlyFormPropsForCommonSiteConfig"
							class="pointer-events-none"
						/>
						<span class="text-base text-gray-600" v-else>
							No keys added. Click on Edit Config to add one.
						</span>
					</div>
				</div>
				<div
					class="hidden max-w-full flex-1 overflow-x-scroll whitespace-pre-line rounded bg-gray-100 p-4 font-mono text-base md:block"
				>
					<div class="mb-4">common_site_config.json</div>
					<div v-html="commonSiteConfigPreview"></div>
				</div>
			</div>
			<div class="mt-4">
				<h2 class="text-xl font-semibold">Bench Config</h2>
				<p class="mt-1.5 mb-4 text-base text-gray-600">
					Add and update key value pairs to your bench's bench_config.json
				</p>
				<div class="flex space-x-4">
					<div class="w-full shrink-0 space-y-4 md:w-2/3">
						<div class="space-y-4" v-if="editMode">
							<div
								class="grid grid-cols-5 gap-4"
								v-for="(config, i) in $resources.benchConfig.data.bench_config"
								:key="i"
							>
								<Input
									type="text"
									placeholder="key"
									value="http_timeout"
									v-model="config.key"
									class="col-span-2"
									:disabled="true"
								/>
								<Input
									type="select"
									placeholder="type"
									v-model="config.type"
									:options="['Number']"
									:disabled="true"
								/>
								<div class="col-span-2 flex items-center">
									<Input
										type="number"
										placeholder="value"
										v-model="config.value"
										@change="isBenchConfigFormDirty = true"
									/>
									<button
										class="ml-2 rounded-md p-1 hover:bg-gray-100"
										@click="removeBenchConfig(config)"
									>
										<FeatherIcon name="x" class="h-5 w-5 text-gray-700" />
									</button>
								</div>
							</div>
							<ErrorMessage :message="$resources.benchConfig.error" />
							<Button
								@click="addBenchConfig"
								v-if="
									editMode &&
									$resources.benchConfig.data.bench_config.length < 1
								"
							>
								Add Key
							</Button>
						</div>
						<div v-else>
							<Form
								v-if="
									readOnlyFormPropsForBenchConfig.fields &&
									readOnlyFormPropsForBenchConfig.fields.length
								"
								v-bind="readOnlyFormPropsForBenchConfig"
								class="pointer-events-none"
							/>
							<span class="text-base text-gray-600" v-else>
								No keys added. Click on Edit Config to add one.
							</span>
						</div>
					</div>
					<div
						class="hidden max-w-full flex-1 overflow-x-scroll whitespace-pre-line rounded bg-gray-100 p-4 font-mono text-base md:block"
					>
						<div class="mb-4">bench_config.json</div>
						<div v-html="benchConfigPreview"></div>
					</div>
				</div>
			</div>
		</Card>
	</div>
</template>

<script>
import Form from '@/components/Form.vue';

export default {
	name: 'BenchConfig',
	components: {
		Form
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
	computed: {
		commonSiteConfigPreview() {
			let obj = {};

			for (let d of this.$resources.benchConfig.data.common_site_config) {
				let value = d.value;
				if (['Boolean', 'Number'].includes(d.type)) {
					value = Number(value);
				} else if (d.type === 'JSON') {
					try {
						value = JSON.parse(value);
					} catch (e) {
						value = {};
					}
				}
				obj[d.key] = value;
			}
			return JSON.stringify(obj, null, '&nbsp; ');
		},
		benchConfigPreview() {
			let obj = {};

			for (let d of this.$resources.benchConfig.data.bench_config) {
				if (d.key === 'http_timeout') obj[d.key] = Number(d.value);
			}
			return JSON.stringify(obj, null, '&nbsp; ');
		},
		readOnlyFormPropsForCommonSiteConfig() {
			if (!this.$resources.standardConfigKeys.data) {
				return {};
			}

			let fields = this.$resources.benchConfig.data.common_site_config.map(
				config => {
					let standardKey = this.$resources.standardConfigKeys.data.find(
						d => d.key === config.key
					);
					return {
						label: standardKey?.title || config.key,
						fieldname: standardKey?.key || config.key
					};
				}
			);

			let modelValue = {};
			for (let d of this.$resources.benchConfig.data.common_site_config) {
				modelValue[d.key] = d.value;
			}

			return { fields, modelValue };
		},
		readOnlyFormPropsForBenchConfig() {
			let data = {
				fields: [],
				modelValue: {}
			};

			const httpTimeout = this.$resources.benchConfig.data.bench_config.find(
				d => d.key === 'http_timeout'
			)?.value;

			if (httpTimeout)
				data = {
					fields: [
						{
							label: 'http_timeout',
							fieldname: 'http_timeout'
						}
					],
					modelValue: {
						http_timeout:
							Number(
								this.$resources.benchConfig.data.bench_config.find(
									d => d.key === 'http_timeout'
								)?.value
							) || ''
					}
				};
			return data;
		}
	},
	methods: {
		configInputProps(config) {
			let type = {
				String: 'text',
				Number: 'number',
				JSON: 'textarea',
				Boolean: 'select'
			}[config.type];
			return {
				type,
				options: config.type === 'Boolean' ? ['1', '0'] : null
			};
		},
		addCommonSiteConfig() {
			this.$resources.benchConfig.data.common_site_config.push({
				key: '',
				value: '',
				type: 'String'
			});
			this.isCommonSiteConfigFormDirty = true;
		},
		removeCommonSiteConfig(config) {
			this.$resources.benchConfig.data.common_site_config =
				this.$resources.benchConfig.data.common_site_config.filter(
					d => d !== config
				);
			this.isCommonSiteConfigFormDirty = true;
		},
		addBenchConfig() {
			this.$resources.benchConfig.data.bench_config.push({
				key: 'http_timeout',
				value: '',
				type: 'String'
			});
			this.isBenchConfigFormDirty = true;
		},
		removeBenchConfig(config) {
			this.$resources.benchConfig.data.bench_config =
				this.$resources.benchConfig.data.bench_config.filter(d => d !== config);
			this.isBenchConfigFormDirty = true;
		},
		updateBenchConfig() {
			if (this.isCommonSiteConfigFormDirty || this.isBenchConfigFormDirty) {
				this.$resources.updateBenchConfig.submit();
			} else {
				this.editMode = false;
				this.isCommonSiteConfigFormDirty = false;
				this.isBenchConfigFormDirty = false;
			}
		},
		onTypeChange(config) {
			if (config.type === 'Boolean') config.value = '1';
			else if (config.type === 'Number')
				config.value = Number(config.value) || 0;
			else if (config.type === 'String') config.value = String(config.value);
		}
	}
};
</script>
