<template>
	<Card :title="title || 'Site Config'">
		<template #actions>
			<Button
				class="mr-2"
				:loading="$resources.configData.loading"
				v-if="isDirty"
				@click="
					() => {
						$resources.configData.reload().then(() => {
							isDirty = false;
						});
					}
				"
			>
				Discard changes
			</Button>
			<Button
				variant="solid"
				v-if="isDirty"
				@click="updateConfig"
				:loading="$resources.updateConfig.loading"
			>
				Save changes
			</Button>
		</template>
		<div class="flex space-x-4">
			<div class="w-full shrink-0 space-y-4 md:w-1/2">
				<div class="ml-2">
					<ErrorMessage :message="$resources.updateConfig.error" />
					<div
						v-if="$resources.configData?.data?.length"
						v-for="config in $resources.configData.data"
						:key="config.key"
						class="mt-2 flex"
					>
						<FormControl
							:label="getStandardConfigTitle(config.key)"
							v-model="config.value"
							@input="isDirty = true"
							class="flex-1"
						/>
						<Button
							class="ml-2 mt-5"
							icon="x"
							variant="ghost"
							@click="removeConfig(config)"
						/>
					</div>
					<p v-else class="my-2 text-base text-gray-600">
						No keys added. Click on Add Key to add one.
					</p>
					<Button class="mt-4" @click="showAddConfigKeyDialog = true"
						>Add Key</Button
					>
				</div>
			</div>
			<div
				class="hidden h-fit max-w-full flex-1 overflow-x-scroll whitespace-pre-line rounded bg-gray-100 p-4 font-mono text-base md:block"
			>
				<div v-if="configName" class="mb-4">{{ configName }}</div>
				<div v-html="configPreview"></div>
			</div>
			<Dialog
				:options="{
					title: 'Add Config Key',
					actions: [
						{
							label: 'Add Key',
							variant: 'solid',
							onClick: addConfig
						}
					]
				}"
				v-model="showAddConfigKeyDialog"
			>
				<template v-slot:body-content>
					<div class="space-y-4">
						<div>
							<span class="mb-1 block text-xs text-gray-600">Key</span>
							<Autocomplete
								placeholder="Key"
								:options="getStandardConfigKeys"
								v-model="chosenStandardConfig"
								@update:modelValue="handleAutocompleteSelection"
							/>
						</div>
						<FormControl
							v-if="showCustomKeyInput"
							v-model="newConfig.key"
							label="Custom Key"
							class="w-full"
							@change="isDirty = true"
						/>
						<FormControl
							label="Type"
							v-model="newConfig.type"
							type="select"
							:disabled="chosenStandardConfig && !showCustomKeyInput"
							:options="['String', 'Number', 'JSON', 'Boolean']"
							@change="isDirty = true"
						/>
						<FormControl
							v-bind="configInputProps()"
							v-model="newConfig.value"
							label="Value"
							class="w-full"
							@change="isDirty = true"
						/>
					</div>
				</template>
			</Dialog>
		</div>
	</Card>
</template>

<script>
import { Autocomplete } from 'frappe-ui';

export default {
	name: 'ConfigEditor',
	components: {
		Autocomplete
	},
	props: [
		'title',
		'subtitle',
		'configName',
		'configData',
		'updateConfigMethod'
	],
	data() {
		return {
			isDirty: false,
			showCustomKeyInput: false,
			showAddConfigKeyDialog: false,
			chosenStandardConfig: {
				title: '',
				key: ''
			},
			newConfig: {
				key: '',
				value: '',
				type: 'String'
			}
		};
	},
	resources: {
		configData() {
			return this.configData();
		},
		updateConfig() {
			function isValidJSON(str) {
				try {
					JSON.parse(str);
					return true;
				} catch (e) {
					return false;
				}
			}
			const updatedConfig = this.$resources.configData.data.map(d => {
				const value = d.value;
				if (!isNaN(value)) d.type = 'Number';
				else if (isValidJSON(value)) d.type = 'JSON';
				else d.type = 'String';

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
					this.$resources.validateKeys.submit({
						keys: JSON.stringify(keys)
					});
					let invalidKeys = this.$resources.validateKeys.data;
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
					this.isDirty = false;
				}
			};
		},
		standardConfigKeys: {
			url: 'press.api.config.standard_keys',
			cache: 'standardConfigKeys',
			auto: true
		},
		validateKeys: {
			url: 'press.api.config.is_valid'
		}
	},
	computed: {
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
		},
		getStandardConfigKeys() {
			return [
				{
					group: 'Custom',
					items: [{ label: 'Create a custom key', value: 'custom_key' }]
				},
				{
					group: 'Standard',
					items: this.$resources.standardConfigKeys.data.map(d => ({
						label: d.title,
						value: d.key
					}))
				}
			];
		}
	},
	methods: {
		configInputProps() {
			let type = {
				String: 'text',
				Number: 'number',
				JSON: 'textarea',
				Boolean: 'select'
			}[this.newConfig.type];

			return {
				type,
				options: this.newConfig.type === 'Boolean' ? ['1', '0'] : null
			};
		},
		addConfig() {
			this.$resources.configData.data.push({
				key: this.getStandardConfigKey(this.newConfig.key),
				value: this.newConfig.value,
				type: this.newConfig.type
			});
			this.isDirty = true;
			this.showAddConfigKeyDialog = false;
		},
		handleAutocompleteSelection() {
			if (this.chosenStandardConfig?.value === 'custom_key') {
				this.showCustomKeyInput = true;
			} else {
				this.showCustomKeyInput = false;
				this.newConfig.type = this.getStandardConfigType(
					this.chosenStandardConfig?.value
				);
			}

			if (this.newConfig.type === 'Boolean') {
				this.newConfig.value = 0;
			} else if (this.newConfig.type === 'JSON') {
				this.newConfig.value = '{}';
			} else {
				this.newConfig.value = '';
			}

			this.newConfig.key = this.chosenStandardConfig?.value || '';
		},
		getStandardConfigType(key) {
			const type =
				this.$resources.standardConfigKeys.data.find(d => d.key === key)
					?.type || 'String';

			return type === 'Password' ? 'String' : type;
		},
		getStandardConfigKey(key) {
			return (
				this.$resources.standardConfigKeys.data.find(d => d.title === key)
					?.key || key
			);
		},
		getStandardConfigTitle(key) {
			return (
				this.$resources.standardConfigKeys.data.find(d => d.key === key)
					?.title || key
			);
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
				this.isDirty = false;
			}
		}
	}
};
</script>
