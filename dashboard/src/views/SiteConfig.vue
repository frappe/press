<template>
	<div class="space-y-10" v-if="site">
		<Card
			title="Site Config"
			subtitle="Add and update key value pairs to your site's site_config.json"
		>
			<template #actions>
				<Button
					icon-left="edit"
					v-if="['Active', 'Broken'].includes(site.status) && !editMode"
					@click="editMode = true"
				>
					Edit Config
				</Button>
				<Button
					v-if="editMode"
					:loading="$resources.siteConfig.loading"
					@click="
						() => {
							$resources.siteConfig.reload().then(() => {
								editMode = false;
								isDirty = false;
							});
						}
					"
				>
					Discard changes
				</Button>
				<Button
					type="primary"
					v-if="editMode"
					@click="updateSiteConfig"
					:loading="$resources.updateSiteConfig.loading"
				>
					Save changes
				</Button>
			</template>
			<div class="flex space-x-4">
				<div class="w-full shrink-0 space-y-4 md:w-2/3">
					<div class="space-y-4" v-if="editMode">
						<div
							class="grid grid-cols-5 gap-4"
							v-for="(config, i) in $resources.siteConfig.data"
							:key="i"
						>
							<Input
								type="text"
								placeholder="key"
								v-model="config.key"
								class="col-span-2"
								@change="isDirty = true"
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
									@change="isDirty = true"
								/>
								<button
									class="ml-2 rounded-md p-1 hover:bg-gray-100"
									@click="removeConfig(config)"
								>
									<FeatherIcon name="x" class="h-5 w-5 text-gray-700" />
								</button>
							</div>
						</div>
						<ErrorMessage :error="$resources.updateSiteConfig.error" />
						<div class="space-x-2">
							<Button @click="addConfig" v-if="!isDirty"> Add Key </Button>
						</div>
					</div>
					<div v-else>
						<Form
							v-if="readOnlyFormProps.fields && readOnlyFormProps.fields.length"
							v-bind="readOnlyFormProps"
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
					<div class="mb-4">site_config.json</div>
					<div v-html="siteConfigPreview"></div>
				</div>
			</div>
		</Card>
	</div>
</template>

<script>
import Form from '@/components/Form.vue';

export default {
	name: 'SiteConfig',
	components: {
		Form
	},
	props: ['site'],
	data() {
		return {
			editMode: false,
			isDirty: false
		};
	},
	resources: {
		siteConfig() {
			return {
				method: 'press.api.site.site_config',
				params: { name: this.site?.name },
				auto: true,
				default: []
			};
		},
		standardConfigKeys: 'press.api.config.standard_keys',
		updateSiteConfig() {
			let updatedConfig = this.$resources.siteConfig.data.map(d => {
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

			return {
				method: 'press.api.site.update_config',
				params: {
					name: this.site?.name,
					config: JSON.stringify(updatedConfig)
				},
				async validate() {
					let keys = updatedConfig.map(d => d.key);
					if (keys.length !== [...new Set(keys)].length) {
						return 'Duplicate key';
					}
					let invalidKeys = await this.$call('press.api.config.is_valid', {
						keys: JSON.stringify(keys)
					});
					if (invalidKeys?.length > 0) {
						return `Invalid key: ${invalidKeys.join(', ')}`;
					}
					for (let config of updatedConfig) {
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
				},
				onSuccess() {
					this.editMode = false;
					this.isDirty = false;
				}
			};
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
		addConfig() {
			this.$resources.siteConfig.data.push({
				key: '',
				value: '',
				type: 'String'
			});
			this.isDirty = true;
		},
		removeConfig(config) {
			this.$resources.siteConfig.data = this.$resources.siteConfig.data.filter(
				d => d !== config
			);
			this.isDirty = true;
		},
		onTypeChange(config) {
			if (config.type === 'Boolean') {
				config.value = '1';
			} else if (config.type === 'Number') {
				config.value = Number(config.value) || 0;
			} else if (config.type === 'String') {
				config.value = String(config.value);
			}
		},
		updateSiteConfig() {
			if (this.isDirty) {
				this.$resources.updateSiteConfig.submit();
			} else {
				this.editMode = false;
				this.isDirty = false;
			}
		}
	},
	computed: {
		siteConfigPreview() {
			let obj = {};

			for (let d of this.$resources.siteConfig.data) {
				let value = d.value;
				if (['Boolean', 'Number'].includes(d.type)) {
					value = Number(d.value);
				} else if (d.type === 'JSON') {
					try {
						value = JSON.parse(d.value);
					} catch (error) {
						value = {};
					}
				}
				obj[d.key] = value;
			}
			return JSON.stringify(obj, null, '&nbsp; ');
		},
		readOnlyFormProps() {
			if (!this.$resources.standardConfigKeys.data) {
				return {};
			}

			let fields = this.$resources.siteConfig.data.map(config => {
				let standardKey = this.$resources.standardConfigKeys.data.find(
					d => d.key === config.key
				);
				return {
					label: standardKey?.title || config.key,
					fieldname: standardKey?.key || config.key
				};
			});

			let modelValue = {};
			for (let d of this.$resources.siteConfig.data) {
				let value = d.value;
				if (['Boolean', 'Number'].includes(d.type)) {
					value = Number(value);
				}
				modelValue[d.key] = value;
			}

			return {
				fields,
				modelValue
			};
		},
		NotAllowed() {
			return `Not Permitted in ${this.site.status} mode`;
		}
	}
};
</script>
