<template>
	<Dialog
		v-model="show"
		:options="{
			title: title,
			actions: [
				{
					label: 'Cancel',
					onClick: hide
				},
				primaryAction
					? {
							...primaryAction,
							onClick: onConfirm
					  }
					: {
							label: 'Confirm',
							variant: 'solid',
							onClick: onConfirm,
							loading: isLoading
					  }
			]
		}"
	>
		<template #body-content>
			<p class="text-base text-gray-800" v-if="message" v-html="message" />
			<div class="space-y-4">
				<FormControl
					v-for="field in fields"
					v-bind="field"
					v-model="values[field.fieldname]"
					:key="field.fieldname"
				/>
			</div>
			<ErrorMessage class="mt-2" :message="error" />
		</template>
	</Dialog>
</template>
<script>
import { ErrorMessage, FormControl } from 'frappe-ui';

export default {
	name: 'ConfirmDialog',
	props: ['title', 'message', 'fields', 'primaryAction', 'onSuccess'],
	data() {
		return {
			show: true,
			error: null,
			isLoading: false,
			values: {}
		};
	},
	components: { FormControl, ErrorMessage },
	methods: {
		onConfirm() {
			this.error = null;
			this.isLoading = true;
			try {
				console.log(this.primaryAction);
				let primaryActionHandler = this.primaryAction?.onClick || this.onSuccess;
				let result = primaryActionHandler({ hide: this.hide, values: this.values });
				if (result?.then) {
					result
						.then(() => (this.isLoading = false))
						.catch(error => (this.error = error));
				}
			} catch (error) {
				this.error = error;
			} finally {
				this.isLoading = false;
			}
		},
		hide() {
			this.show = false;
		}
	}
};
</script>
