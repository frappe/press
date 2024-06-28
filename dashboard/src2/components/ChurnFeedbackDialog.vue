<template>
	<Dialog
		:options="{
			title: 'Tell us why you are leaving',
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
		v-model="show"
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
				required
			/>
			<FormControl
				class="mt-4"
				type="textarea"
				variant="outline"
				placeholder="I am leaving Frappe Cloud because..."
				size="md"
				v-model="note"
			/>
			<ErrorMessage class="mt-2" :message="$resources.submitFeedback.error" />
		</template>
	</Dialog>
</template>

<script>
import FormControl from 'frappe-ui/src/components/FormControl.vue';

export default {
	name: 'ChurnFeedbackDialog',
	emits: ['updated'],
	props: ['team'],
	data() {
		return {
			feedback: '',
			route: '',
			note: '',
			show: true
		};
	},
	resources: {
		submitFeedback() {
			return {
				url: 'press.api.account.feedback',
				makeParams() {
					return {
						team: this.team,
						message: this.feedback,
						route: this.$route?.name,
						note: this.note
					};
				},
				validate() {
					if (this.feedback === 'My reason is not listed here' && !this.note) {
						return 'Please provide a reason';
					}
				},
				onSuccess() {
					this.show = false;
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
				'Frappe Cloud is too expensive for me',
				'I was just exploring the platform',
				'My reason is not listed here'
			];
		}
	}
};
</script>
