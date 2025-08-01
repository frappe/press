<template>
	<Dialog v-model="showDialog" :options="{ title }">
		<template #body-content>
			<div class="space-y-4">
				<p class="text-p-base text-gray-800" v-if="message" v-html="message" />
				<div class="space-y-4">
					<template v-for="field in fields" :key="field.fieldname">
						<LinkControl
							v-if="field.type == 'link'"
							v-bind="field"
							v-model="values[field.fieldname]"
							v-show="
								typeof field.condition === 'function'
									? field.condition(this.values)
									: true
							"
						/>
						<FormControl
							v-else
							v-bind="field"
							v-model="values[field.fieldname]"
							v-show="
								typeof field.condition === 'function'
									? field.condition(this.values)
									: true
							"
						/>
					</template>
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
import LinkControl from '../components/LinkControl.vue';

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
				}, {}),
		};
	},
	components: { FormControl, ErrorMessage, LinkControl },
	methods: {
		onConfirm() {
			this.error = null;
			try {
				let primaryActionHandler =
					this.primaryAction?.onClick || this.onSuccess;
				let result = primaryActionHandler({
					hide: this.hide,
					values: this.values,
				});
				if (result?.then) {
					this.isLoading = true;
					result
						.then(() => (this.isLoading = false))
						.catch((error) => {
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
		},
		handleKeydown(event) {
			if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
				event.preventDefault();
				this.onConfirm();
			}
		},
	},
	mounted() {
		document.addEventListener('keydown', this.handleKeydown);
	},
	beforeUnmount() {
		document.removeEventListener('keydown', this.handleKeydown);
	},
	computed: {
		primaryActionProps() {
			return {
				label: 'Confirm',
				variant: 'solid',
				...this.primaryAction,
				loading: this.isLoading,
				onClick: this.onConfirm,
			};
		},
	},
};
</script>
