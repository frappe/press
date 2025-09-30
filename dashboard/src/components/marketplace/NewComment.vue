<template>
	<div v-if="show" class="p-2">
		<FormControl
			:type="'textarea'"
			size="sm"
			variant="subtle"
			placeholder="Enter your comments here"
			:disabled="false"
			label="Comment"
			v-model="newComment"
		/>
		<div class="flex justify-end mt-2">
			<Button
				:variant="'solid'"
				theme="gray"
				size="sm"
				@click="submitComment"
				:disabled="!newComment.trim()"
			>
				Comment
			</Button>
		</div>
	</div>
</template>

<script>
export default {
	props: ['approval_request_name', 'filename', 'line_number'],
	data() {
		return {
			show: true,
			newComment: '',
		};
	},
	methods: {
		submitComment() {
			const commentData = {
				name: this.approval_request_name,
				filename: this.filename,
				line_number: this.line_number,
				comment: this.newComment,
			};
			this.$resources.addComment.submit(commentData);
			this.newComment = '';
			this.$emit('comment-submitted');
		},
	},
	resources: {
		addComment() {
			return {
				url: 'press.api.marketplace.add_code_review_comment',
				method: 'POST',
			};
		},
	},
};
</script>
