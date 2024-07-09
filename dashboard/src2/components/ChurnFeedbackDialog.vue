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
			<div class="mt-3">
				<span class="mb-2 block text-sm leading-4 text-gray-600">
					Please rate your experience
				</span>
				<StarRatingInput v-model="rating" />
			</div>
			<FormControl
				class="mt-4"
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
import StarRatingInput from '../../src/components/StarRatingInput.vue';

export default {
	name: 'ChurnFeedbackDialog',
	emits: ['updated'],
	props: ['team'],
	components: {
		StarRatingInput
	},
	data() {
		return {
			feedback: '',
			route: '',
			note: '',
			show: true,
			rating: 5
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
						note: this.note,
						rating: this.rating
					};
				},
				validate() {
					if (
						[
							'Payment issues',
							'Features were missing',
							'My reason is not listed here'
						].includes(this.feedback) &&
						!this.note
					) {
						return 'Please provide a brief reason';
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
				'I am moving to a different product e.g ZOHO, Quickbooks, etc.',
				'I was just exploring the product',
				'I prefer self-hosting my instance',
				'Moved site to another Frappe Cloud account',
				'I did not like the Frappe Cloud experience',
				'Frappe Cloud is too expensive for me',
				'Payment issues',
				'Features were missing',
				'My reason is not listed here'
			];
		}
	}
};
</script>
