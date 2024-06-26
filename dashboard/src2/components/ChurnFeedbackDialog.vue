<template>
	<Dialog
		:options="{
			title: 'Your feedback matters!',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					loading: $resources.submitFeedback.loading,
					onClick: () => {
						$resources.submitFeedback.submit({
							feedback: this.feedback
						});
					}
				}
			]
		}"
		:modelValue="show"
		@update:modelValue="$emit('update:show', $event)"
	>
		<template v-slot:body-content>
			<p class="mb-5 text-sm text-gray-800">
				Help us improve your experience by sharing your thoughts.
			</p>
			<FormControl
				type="select"
				:options="options"
				size="md"
				variant="outline"
				placeholder="Select a reason"
				v-model="feedback"
			/>
			<FormControl
				class="mt-4"
				type="textarea"
				variant="outline"
				placeholder="Add a note (optional)"
				size="md"
				v-model="note"
			/>
			<ErrorMessage class="mt-2" :message="$resources.submitFeedback.error" />
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';
import FormControl from 'frappe-ui/src/components/FormControl.vue';

export default {
	name: 'ChurnFeedbackDialog',
	props: ['show'],
	emits: ['update:show', 'updated'],
	data() {
		return {
			feedback: '',
			route: '',
			note: ''
		};
	},
	resources: {
		submitFeedback() {
			return {
				url: 'press.api.account.feedback',
				makeParams() {
					return {
						message: this.feedback,
						route: this.$route?.name
					};
				},
				onSuccess() {
					this.$emit('update:show', false);
					notify({
						title: 'Feedback submitted'
					});
					this.$emit('updated');
				}
			};
		}
	},
	computed: {
		options() {
			return [
				'I am not satisfied with the service',
				'I am moving to a different service',
				'I am not using the service anymore',
				'Other'
			];
		}
	}
};
</script>
