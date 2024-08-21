<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Code Review',
			size: '6xl'
		}"
	>
		<template v-if="getResults" #body-content>
			<div class="container mx-auto px-4 py-3">
				<div class="grid gap-3">
					<div
						class="card bg-white shadow-md rounded-md overflow-hidden"
						v-for="file in getResults"
						:key="file.name"
					>
						<div class="card-header bg-gray-200 p-3">
							<h2 class="text-md font-semibold text-gray-800">
								{{ file.name }} - {{ file.score }} issues
							</h2>
						</div>
						<div class="p-4">
							<div
								class="issues space-y-4"
								v-for="line in file.lines"
								:key="line.context.line_number"
							>
								<div
									class="issue-item p-4 mb-4"
									v-for="issue in line.issues"
									:key="issue.violation"
								>
									<div class="flex items-center mb-3">
										<span class="text-red-600 mr-2">{{ issue.severity }}</span>
										<span class="text-gray-800">({{ issue.violation }})</span>
										<span class="text-orange-500 font-semibold pl-2">
											- {{ issue.match }}</span
										>
									</div>
									<div class="border border-gray-400 p-2 rounded-md">
										<div
											v-for="(lineText, i) in line.context.lines"
											:key="i"
											:class="{
												'bg-yellow-200':
													lineText.includes(issue.match) &&
													line.context.line_range[i] ===
														line.context.line_number
											}"
										>
											<code class="p-2 text-sm whitespace-pre-wrap">
												<span class="text-gray-300"
													>{{ line.context.line_range[i] }}:</span
												>
												{{ lineText }}
											</code>
										</div>
										<div
											v-if="
												getCommentsForLine(file.name, line.context.line_number)
													.length
											"
										>
											<hr class="h-1 mt-2" />
											<div
												class="comment-item mt-2 p-2"
												v-for="comment in getCommentsForLine(
													file.name,
													line.context.line_number
												)"
												:key="comment.name"
											>
												<strong class="pr-1">
													{{ comment.commented_by }} </strong
												>({{ formatTime(comment.time) }})
												<p>
													{{ comment.comment }}
												</p>
											</div>
										</div>
										<NewComment
											:approval_request_name="row.approval_request_name"
											:filename="file.name"
											:line_number="line.context.line_number"
											@comment-submitted="handleCommentSubmitted"
										/>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import NewComment from './NewComment.vue';

export default {
	components: {
		NewComment
	},
	props: ['row', 'app'],
	data() {
		return {
			show: true
		};
	},
	computed: {
		getResults() {
			if (this.$resources.codeScreening.doc) {
				const results = JSON.parse(this.$resources.codeScreening.doc.result);
				return results;
			}
		},
		getComments() {
			if (this.$resources.codeScreening.doc) {
				const results = this.$resources.codeScreening.doc.code_comments;
				return results;
			}
		},
		user() {
			return this.$team?.doc?.user_info;
		}
	},
	methods: {
		getCommentsForLine(filename, lineNumber) {
			// Filter comments by matching filename and line number
			let filteredComments = this.getComments.filter(
				comment =>
					comment.filename === filename && comment.line_number === lineNumber
			);

			// Sort comments by time in descending order (latest first)
			filteredComments.sort((a, b) => new Date(a.time) - new Date(b.time));

			return filteredComments;
		},
		formatTime(time) {
			const date = new Date(time);
			return date.toLocaleString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
				second: '2-digit',
				hour12: true
			});
		},
		handleCommentSubmitted() {
			this.$resources.codeScreening.reload();
		}
	},
	resources: {
		codeScreening() {
			return {
				type: 'document',
				doctype: 'App Release Approval Request',
				name: this.row.approval_request_name,
				fields: [
					'name',
					'marketplace_app',
					'screening_status',
					'app_release',
					'status',
					'result',
					'code_comments'
				],
				auto: true
			};
		}
	}
};
</script>
