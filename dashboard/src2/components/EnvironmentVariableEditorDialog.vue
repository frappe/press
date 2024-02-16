<template>
	<Dialog
		:options="{
			title: environment_variable ? 'Edit Environment Variable' : 'Add Environment Variable',
			actions: [
				{
					label: environment_variable ? 'Edit Environment Variable' : 'Add Environment Variable',
					variant: 'solid',
					loading: docResource?.updateEnvironmentVariable?.loading,
					onClick: updateEnvironmentVariable
				}
			]
		}"
		v-model="showDialog"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<FormControl
					type="text"
					label="Key"
					v-model="key"
					autocomplete="off"
				/>
				<FormControl
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
	name: 'EnvironmentVariableEditorDialog',
	props: ['group', 'environment_variable'],
	components: {
		Autocomplete,
		FormControl,
		ErrorMessage
	},
	data() {
		return {
			docResource: null,
			showDialog: true,
			key: null,
			value: null,
			error: null
		};
	},
	async mounted() {
		if (this.environment_variable) {
			this.key = this.environment_variable.key;
			this.value = this.environment_variable.value;
		}
	},
	methods: {
		updateEnvironmentVariable() {
			if (this.group) {
				this.docResource = getCachedDocumentResource(
					'Release Group',
					this.group
				);
			}
			if (!this.docResource) return;
			let key = this.key;
			let value = this.value;
			let environment_variables = { [key]: value };
			this.docResource.updateEnvironmentVariable.submit(
				{ environment_variables },
				{
					onSuccess: () => {
						this.$emit('success');
						this.showDialog = false;
					}
				}
			);
			this.error = this.docResource.updateEnvironmentVariable.error;
		}
	},
};
</script>
