<template>
	<div class="space-y-10">
		<Section
			title="Site Config"
			description="Add key value pairs to your site's site_config.json"
		>
			<div class="flex space-x-4">
				<SectionCard class="px-6 py-6 space-y-4 md:w-2/3">
					<div class="space-y-4" v-if="editMode">
						<div
							class="grid grid-cols-5 gap-4"
							v-for="(config, i) in siteConfigList"
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
							/>
							<div class="flex items-center col-span-2">
								<Input
									class="w-full"
									v-bind="configInputProps(config)"
									:input-class="{ 'font-mono': config.type === 'JSON' }"
									placeholder="value"
									v-model="config.value"
									@change="isDirty = true"
								/>
								<button
									class="p-1 ml-2 rounded-md hover:bg-gray-100"
									@click="removeConfig(config)"
								>
									<FeatherIcon name="x" class="w-5 h-5 text-gray-700" />
								</button>
							</div>
						</div>
						<ErrorMessage :error="$resources.updateSiteConfig.error" />
						<div class="space-x-2">
							<Button @click="addConfig" v-if="!isDirty">
								Add Key
							</Button>
							<Button
								v-else
								@click="$resources.updateSiteConfig.submit()"
								:loading="$resources.updateSiteConfig.loading"
							>
								Update Config
							</Button>
						</div>
					</div>

					<div v-else>
						<Form
							:fields="siteConfigFields"
							v-model="siteConfig"
							class="pointer-events-none"
						/>
						<div class="mt-4">
							<Button @click="editMode = !editMode">Edit Config</Button>
						</div>
					</div>
				</SectionCard>
				<div
					class="flex-1 p-4 font-mono text-base whitespace-pre-line bg-gray-100 rounded"
				>
					<div class="mb-4">site_config.json</div>
					<div v-html="siteConfigPreview"></div>
				</div>
			</div>
		</Section>
	</div>
</template>

<script>
import Form from '@/components/Form';

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
		standardConfigKeys: 'press.api.config.standard_keys',
		updateSiteConfig() {
			let updatedConfig = this.site.config.map(d => {
				let value = d.value;
				if (d.type === 'Boolean') {
					value = d.value === 'true' ? true : false;
				} else if (d.type === 'Number') {
					value = Number(d.value);
				} else if (d.type == "JSON") {
					try {
						value = JSON.parse(d.value || "{}");
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
					name: this.site.name,
					config: JSON.stringify(updatedConfig)
				},
				validate() {
					let keys = updatedConfig.map(d => d.key);
					if (keys.length !== [...new Set(keys)].length) {
						return 'Duplicate key';
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
				options: config.type === 'Boolean' ? ['true', 'false'] : null
			};
		},
		addConfig() {
			this.site.config.push({ key: '', value: '', type: 'String' });
			this.isDirty = true;
		},
		removeConfig(config) {
			this.site.config = this.site.config.filter(d => d !== config);
			this.isDirty = true;
		}
	},
	computed: {
		siteConfigPreview() {
			return JSON.stringify(this.siteConfig, null, '&nbsp;');
		},
		siteConfigList() {
			return (this.site.config || []).filter(d => !d.toRemove);
		},
		siteConfigFields() {
			if (!this.$resources.standardConfigKeys.data) {
				return [];
			}
			let fields = [];
			for (let key in this.siteConfig) {
				let standardKey = this.$resources.standardConfigKeys.data.find(
					d => d.key === key
				);
				fields.push({
					label: standardKey?.title || key,
					fieldname: standardKey?.key || key
				});
			}
			return fields;
		},
		siteConfig() {
			let obj = {};

			for (let d of this.site.config) {
				let value = null;
				if (d.type === 'Boolean') {
					value = Boolean(d.value);
				} else if (d.type === 'Number') {
					value = Number(d.value);
				} else if (d.type == "JSON") {
					value = JSON.parse(d.value || "{}");
				} else {
					value = d.value
				}
				obj[d.key] = value;
			}
			return obj;
		}
	}
};
</script>
