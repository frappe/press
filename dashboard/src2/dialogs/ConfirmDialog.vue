<template>
	<Dialog v-model="showDialog" :options="{ title }">
		<template #body-content>
			<div class="space-y-4">
				<p class="text-p-base text-gray-800" v-if="message" v-html="message" />
				<div class="space-y-4">
					<FormControl
						v-for="field in fields"
						v-bind="field"
						v-model="values[field.fieldname]"
						:key="field.fieldname"
					/>
				</div>
			</div>
			<ErrorMessage class="mt-2" :message="error" />
		</template>
		<template #actions>
			<Button class="w-full" v-bind="primaryActionProps" />
		</template>
	</Dialog>
</template>
<script>
import { ErrorMessage, FormControl } from 'frappe-ui';

export default {
	name: 'ConfirmDialog',
	props: ['title', 'message', 'fields', 'primaryAction', 'onSuccess'],
	expose: ['show', 'hide'],
	data() {
		return {
			showDialog: true,
			error: null,
			isLoading: false,
			values:
				// set default values for fields
				this.fields.reduce((acc, field) => {
					acc[field.fieldname] = field.default || null;
					return acc;
				}, {})
		};
	},
	components: { FormControl, ErrorMessage },
	methods: {
		onConfirm() {
			this.error = null;
			try {
				let primaryActionHandler =
					this.primaryAction?.onClick || this.onSuccess;
				let result = primaryActionHandler({
					hide: this.hide,
					values: this.values
				});
				if (result?.then) {
					this.isLoading = true;
					result
						.then(() => (this.isLoading = false))
						.catch(error => {
							this.error = error;
							this.isLoading = false;
						});
				}
			} catch (error) {
				this.error = error;
				this.isLoading = false;
			}
		},
		show() {
			this.showDialog = true;
		},
		hide() {
			this.showDialog = false;
		}
	},
	computed: {
		primaryActionProps() {
			return {
				label: 'Confirm',
				variant: 'solid',
				...this.primaryAction,
				loading: this.isLoading,
				onClick: this.onConfirm
			};
		}
	}
};
</script>
