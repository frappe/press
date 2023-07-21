<template>
	<Card :title="title" :subtitle="subtitle">
		<template #actions>
			<Button icon-left="edit" v-if="!editMode" @click="editMode = true">
				Edit Config
			</Button>
			<Button
				v-if="editMode"
				:loading="$resources.configData.loading"
				@click="
					() => {
						$resources.configData.reload().then(() => {
							editMode = false;
							isDirty = false;
						});
					}
				"
			>
				Discard changes
			</Button>
			<Button
				appearance="primary"
				v-if="editMode"
				@click="updateConfig"
				:loading="$resources.updateConfig.loading"
			>
				Save changes
			</Button>
		</template>
		<div class="flex space-x-4">
			<div class="w-full shrink-0 space-y-4 md:w-2/3">
				<div class="space-y-4" v-if="editMode">
					<div
						class="grid grid-cols-5 gap-4"
						v-for="(config, i) in $resources.configData.data"
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
					<ErrorMessage :message="$resources.updateConfig.error" />
					<Button @click="addConfig()" v-if="editMode">Add Key</Button>
				</div>
				<div v-else>
					<Form
						v-if="readOnlyFormProps.fields?.length"
						v-bind="readOnlyFormProps"
						class="pointer-events-none"
					/>
					<span v-else class="text-base text-gray-600">
						No keys added. Click on Edit Config to add one.
					</span>
				</div>
			</div>
			<div
				class="hidden max-w-full flex-1 overflow-x-scroll whitespace-pre-line rounded bg-gray-100 p-4 font-mono text-base md:block"
			>
				<div v-if="configName" class="mb-4">{{ configName }}</div>
				<div v-html="configPreview"></div>
			</div>
		</div>
	</Card>
</template>

<script>
import Form from '@/components/Form.vue';

export default {
	name: 'ConfigEditor',
	components: {
		Form
	},
	props: [
		'title',
		'subtitle',
		'configName',
		'configData',
		'updateConfigMethod',
		'standardConfigKeys'
	],
	data() {
		return {
			isDirty: false,
			editMode: false
		};
	},
	resources: {
		configData() {
			return this.configData();
		},
		updateConfig() {
			const updatedConfig = this.$resources.configData.data.map(d => {
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
				...this.updateConfigMethod(updatedConfig),
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
		},
		standardConfigKeys: 'press.api.config.standard_keys'
	},
	computed: {
		readOnlyFormProps() {
			if (!this.$resources.standardConfigKeys.data) {
				return {};
			}

			let fields = this.$resources.configData.data.map(config => {
				let standardKey = this.$resources.standardConfigKeys.data.find(
					d => d.key === config.key
				);
				return {
					label: standardKey?.title || config.key,
					fieldname: standardKey?.key || config.key
				};
			});

			let modelValue = {};
			for (let d of this.$resources.configData.data) {
				modelValue[d.key] = d.value;
			}

			return {
				fields,
				modelValue
			};
		},
		configPreview() {
			let obj = {};

			for (let d of this.$resources.configData.data) {
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
			this.$resources.configData.data.push({
				key: '',
				value: '',
				type: 'String'
			});
			this.isDirty = true;
		},
		removeConfig(config) {
			const index = this.$resources.configData.data.indexOf(config);
			if (index > -1) this.$resources.configData.data.splice(index, 1);
			this.isDirty = true;
		},
		updateConfig() {
			if (this.isDirty) {
				this.$resources.updateConfig.submit();
			} else {
				this.editMode = false;
				this.isDirty = false;
			}
		},
		onTypeChange(config) {
			if (config.type === 'Boolean') {
				config.value = '1';
			} else if (config.type === 'Number') {
				config.value = Number(config.value) || 0;
			} else if (config.type === 'String') {
				config.value = String(config.value);
			}
		}
	}
};
</script>
