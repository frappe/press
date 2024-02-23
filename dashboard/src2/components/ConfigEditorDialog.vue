<template>
	<Dialog
		:options="{
			title: config ? 'Edit Config' : 'Add Config',
			actions: [
				{
					label: config ? 'Edit Key' : 'Add Key',
					variant: 'solid',
					loading: docResource?.updateConfig?.loading,
					onClick: addConfig
				}
			]
		}"
		v-model="showDialog"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<div :class="{ 'pointer-events-none': config }">
					<FormControl
						type="autocomplete"
						label="Config Name"
						:options="keyOptions"
						v-model="selectedConfig"
					/>
				</div>
				<FormControl
					type="text"
					label="Key"
					:modelValue="
						selectedConfig?.value === '__custom_key'
							? key
							: selectedConfig?.value
					"
					@update:modelValue="
						selectedConfig?.value === '__custom_key' ? (key = $event) : null
					"
					:disabled="selectedConfig?.value !== '__custom_key'"
					autocomplete="off"
				/>
				<FormControl
					type="select"
					label="Type"
					:modelValue="selectedConfig?.type || type"
					@update:modelValue="type = $event"
					:options="[
						'String',
						'Number',
						'JSON',
						'Boolean',
						selectedConfig?.value !== '__custom_key' ? 'Password' : null
					]"
					:disabled="selectedConfig?.value !== '__custom_key'"
					autocomplete="off"
				/>
				<FormControl
					v-bind="valueInputProps"
					label="Value"
					v-model="value"
					autocomplete="off"
				/>
				<ErrorMessage class="mt-2" :message="error" />
			</div>
		</template>
	</Dialog>
</template>
<script>
import {
	Autocomplete,
	ErrorMessage,
	FormControl,
	getCachedDocumentResource
} from 'frappe-ui';

export default {
	name: 'ConfigEditorDialog',
	props: ['site', 'group', 'config'],
	components: {
		Autocomplete,
		FormControl,
		ErrorMessage
	},
	data() {
		return {
			docResource: null,
			showDialog: true,
			selectedConfig: null,
			key: null,
			type: null,
			value: null,
			error: null
		};
	},
	async mounted() {
		if (this.config) {
			await this.$resources.standardKeys.list.promise;
			this.selectedConfig = this.keyOptions.find(
				option => this.config.key === option.value
			);
			if (this.selectedConfig) {
				this.key = this.selectedConfig?.value;
				this.type = this.selectedConfig?.type;
			} else {
				this.selectedConfig = this.keyOptions.find(
					option => '__custom_key' === option.value
				);
				this.key = this.config.key;
				this.type = this.config.type;
			}
			this.value = this.config.type === 'Password' ? '' : this.config.value;
		}
	},
	resources: {
		standardKeys() {
			return {
				type: 'list',
				doctype: 'Site Config Key',
				fields: ['name', 'key', 'title', 'description', 'type'],
				filters: { internal: false },
				orderBy: 'title asc',
				pageLength: 1000,
				auto: true
			};
		}
	},
	methods: {
		addConfig() {
			if (this.site) {
				this.docResource = getCachedDocumentResource('Site', this.site);
			} else if (this.group) {
				this.docResource = getCachedDocumentResource(
					'Release Group',
					this.group
				);
			}
			if (!this.docResource) return;
			let key =
				this.selectedConfig?.value == '__custom_key'
					? this.key
					: this.selectedConfig?.value;
			let type = this.selectedConfig?.type || this.type;
			let value = this.value;
			if (type === 'JSON') {
				try {
					value = JSON.parse(value);
				} catch (e) {
					this.error = 'Invalid JSON';
					return;
				}
			} else if (type === 'Boolean') {
				value = value === '1' ? true : false;
			} else if (type === 'Number') {
				value = Number(value);
			}

			let config = { [key]: value };

			this.docResource.updateConfig.submit(
				{ config },
				{
					onSuccess: () => {
						this.$emit('success');
						this.showDialog = false;
					}
				}
			);
			this.error = this.docResource.updateConfig.error;
		}
	},
	computed: {
		keyOptions() {
			let customKeyOption = {
				label: 'Custom Key',
				value: '__custom_key'
			};
			let standardKeyOptions = (this.$resources.standardKeys.data || []).map(
				key => ({
					label: key.title,
					value: key.key,
					type: key.type
				})
			);
			return [customKeyOption, ...standardKeyOptions];
		},
		valueInputProps() {
			let type = {
				String: 'text',
				Number: 'number',
				JSON: 'textarea',
				Boolean: 'select'
			}[this.selectedConfig?.type || this.type];

			return {
				type,
				options: type === 'select' ? ['1', '0'] : null
			};
		}
	}
};
</script>
