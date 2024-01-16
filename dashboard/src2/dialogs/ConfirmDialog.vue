<template>
	<Dialog v-model="show" :options="{ title }">
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
				let primaryActionHandler =
					this.primaryAction?.onClick || this.onSuccess;
				let result = primaryActionHandler({
					hide: this.hide,
					values: this.values
				});
				if (result?.then) {
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
		hide() {
			this.show = false;
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
