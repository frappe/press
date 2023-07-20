<template>
	<div>
		<div v-if="title" class="flex items-baseline justify-between">
			<h2 class="text-xl font-semibold">{{ title }}</h2>
			<slot name="actions" />
		</div>
		<p v-if="subtitle" class="mt-1.5 mb-4 text-base text-gray-600">
			{{ subtitle }}
		</p>
		<div class="flex space-x-4">
			<div class="w-full shrink-0 space-y-4 md:w-2/3">
				<div class="space-y-4" v-if="editMode">
					<div
						class="grid grid-cols-5 gap-4"
						v-for="(config, i) in configData"
						:key="i"
					>
						<Input
							type="text"
							:disabled="!!customAddConfig"
							placeholder="key"
							v-model="config.key"
							class="col-span-2"
							@change="$emit('isDirty', true)"
						/>
						<Input
							type="select"
							:disabled="!!customAddConfig"
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
								@change="$emit('isDirty', true)"
							/>
							<button
								class="ml-2 rounded-md p-1 hover:bg-gray-100"
								@click="removeConfig(config)"
							>
								<FeatherIcon name="x" class="h-5 w-5 text-gray-700" />
							</button>
						</div>
					</div>
					<Button
						@click="addConfig()"
						v-if="editMode && configData.length < (maxNoOfConfigs || Infinity)"
						>Add Key</Button
					>
				</div>
				<div v-else>
					<Form
						v-if="readOnlyFormProps.fields && readOnlyFormProps.fields.length"
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
				<div class="mb-4">bench_config.json</div>
				<div v-html="configPreview"></div>
			</div>
		</div>
	</div>
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
		'editMode',
		'configData',
		'standardConfigKeys',
		'customAddConfig',
		'maxNoOfConfigs'
	],
	computed: {
		readOnlyFormProps() {
			if (!this.standardConfigKeys) {
				return {};
			}

			let fields = this.configData.map(config => {
				let standardKey = this.standardConfigKeys.find(
					d => d.key === config.key
				);
				return {
					label: standardKey?.title || config.key,
					fieldname: standardKey?.key || config.key
				};
			});

			let modelValue = {};
			for (let d of this.configData) {
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
		configPreview() {
			let obj = {};

			for (let d of this.configData) {
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
			if (this.customAddConfig) this.configData.push(this.customAddConfig());
			else
				this.configData.push({
					key: '',
					value: '',
					type: 'String'
				});
			this.$emit('isDirty', true);
		},
		removeConfig(config) {
			const index = this.configData.indexOf(config);
			if (index > -1) this.configData.splice(index, 1);
			this.$emit('isDirty', true);
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
