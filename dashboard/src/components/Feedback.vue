<template>
	<div>
		<Button @click="isOpen = true">Feedback</Button>
		<Dialog
			:title="submitted ? '' : 'Feedback'"
			v-model="isOpen"
			@change="handleClose"
		>
			<template v-if="!submitted">
				<p class="mb-4 text-base text-gray-900">
					Your feedback will help us decide which features to improve or which
					new features work on next.
				</p>
				<textarea
					class="form-textarea w-full resize-none"
					rows="4"
					placeholder="Your feedback"
					v-model="message"
				>
				</textarea>
				<ErrorMessage class="mt-2" :error="$resources.feedback.error" />
				<Button
					type="primary"
					slot="actions"
					@click="$resources.feedback.submit()"
					:loading="$resources.feedback.loading"
				>
					Submit Feedback
				</Button>
			</template>
			<SuccessCard class="mb-4" title="Thanks for your feedback!" v-else>
				Your feedback helps improve Frappe Cloud.
			</SuccessCard>
		</Dialog>
	</div>
</template>

<script>
export default {
	name: 'Feedback',
	data() {
		return {
			isOpen: false,
			message: null,
			submitted: false
		};
	},
	resources: {
		feedback() {
			return {
				method: 'press.api.account.feedback',
				params: {
					message: this.message,
					route: this.$route.fullPath
				},
				validate() {
					if (!this.message) {
						return 'Message is required';
					}
				},
				onSuccess() {
					this.submitted = true;
				}
			};
		}
	},
	methods: {
		handleClose(isOpen) {
			if (!isOpen) {
				this.submitted = false;
				this.message = null;
			}
		}
	}
};
</script>
