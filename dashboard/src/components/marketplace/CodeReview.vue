<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Code Review',
			size: '6xl',
		}"
	>
		<template v-if="getResults" #body-content>
			<div class="container mx-auto px-4">
				<div class="grid gap-3">
					<div class="flex items-center mb-2">
						<div class="flex items-center">
							<span class="text-lg font-medium text-gray-700 mr-2"
								>Status:</span
							>
							<Badge
								:variant="'subtle'"
								size="lg"
								:label="$resources.codeScreening.doc.status"
								:theme="getBadgeTheme"
							/>
						</div>
						<!-- <Button
							iconLeft="check"
							v-if="
								isSystemUser && $resources.codeScreening.doc.status == 'Open'
							"
							:variant="'subtle'"
							theme="gray"
							size="sm"
							class="mr-4 ml-auto"
							@click="approveRelease"
						>
							Approve Release
						</Button>
						<Button
							iconLeft="x"
							v-if="
								isSystemUser && $resources.codeScreening.doc.status == 'Open'
							"
							:variant="'subtle'"
							theme="gray"
							size="sm"
							class="mr-4"
							@click="showRejectReleaseDialog = true"
						>
							Reject Release
						</Button> -->
					</div>
					<Dialog
						v-model="showRejectReleaseDialog"
						:options="{
							title: 'Confirm',
							size: 'xl',
							actions: [
								{
									label: 'Reject Release',
									variant: 'solid',
									onClick: rejectRelease,
								},
							],
						}"
					>
						<template #body-content>
							<FormControl
								:type="'textarea'"
								size="sm"
								variant="subtle"
								placeholder="Enter your reasons for rejection"
								:disabled="false"
								v-model="rejectionReason"
							/>
						</template>
					</Dialog>

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
											style="background-color: #d1f8d9"
											class="border rounded-md"
										>
											<div
												v-for="(lineText, i) in line.context.lines"
												:key="i"
												:class="{
													'bg-yellow-200 border rounded-md':
														lineText.includes(issue.match) &&
														line.context.line_range[i] ===
															line.context.line_number,
												}"
											>
												<code class="p-2 text-sm whitespace-pre-wrap">
													<span>{{ line.context.line_range[i] }}:</span>
													{{ lineText }}
												</code>
											</div>
										</div>
										<div
											v-if="
												getCommentsForLine(file.name, line.context.line_number)
													.length
											"
										>
											<hr class="h-2 mt-2" />
											<div
												class="comment-item mt-2 p-2"
												v-for="comment in getCommentsForLine(
													file.name,
													line.context.line_number,
												)"
												:key="comment.name"
											>
												<div class="flex items-center">
													<Avatar
														:shape="'circle'"
														:image="null"
														:label="comment.commented_by"
														size="md"
													/>

													<strong class="text-gray-900 pl-2 pr-2 text-lg">
														{{ comment.commented_by }}
													</strong>
													<Tooltip
														:text="formatTime(comment.time)"
														:placement="'top'"
													>
														<span class="text-gray-600 text-sm">
															{{ $dayjs(comment.time).fromNow() }}
														</span>
													</Tooltip>
												</div>
												<p class="text-gray-800 text-base p-2 ml-6">
													{{ comment.comment }}
												</p>
											</div>
										</div>
										<hr class="h-2 mt-2" />
										<NewComment
											v-if="$resources.codeScreening.doc.status == 'Open'"
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
import { toast } from 'vue-sonner';

export default {
	components: {
		NewComment,
	},
	props: ['row', 'app', 'isSystemUser'],
	data() {
		return {
			show: true,
			showRejectReleaseDialog: false,
			rejectionReason: '',
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
		getBadgeTheme() {
			const status = this.$resources.codeScreening.doc.status.toLowerCase();
			if (status === 'open') {
				return 'blue';
			} else if (status === 'approved') {
				return 'green';
			} else {
				return 'red';
			}
		},
	},
	methods: {
		getCommentsForLine(filename, lineNumber) {
			// Filter comments by matching filename and line number
			let filteredComments = this.getComments.filter(
				(comment) =>
					comment.filename === filename && comment.line_number === lineNumber,
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
				hour12: true,
			});
		},
		handleCommentSubmitted() {
			// DB write takes sometime. Instant reload wont be able to reflect changes so quickly. Ideally the cache should be updadted client side
			setTimeout(() => {
				this.$resources.codeScreening.reload();
			}, 1200);
		},
		approveRelease() {
			this.$resources.codeScreening.setValue.submit({
				status: 'Approved',
				reviewed_by: this.$team?.doc?.user,
			});
		},
		rejectRelease() {
			// Check if the rejection reason is empty
			if (!this.rejectionReason) {
				toast.error('Reason for rejection is mandatory');
				return;
			}
			// Proceed with the rejection if the reason is provided
			this.$resources.codeScreening.setValue.submit({
				status: 'Rejected',
				reason_for_rejection: this.rejectionReason,
				reviewed_by: this.$team?.doc?.user,
			});
			this.showRejectReleaseDialog = false;
		},
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
					'code_comments',
				],
				auto: true,
			};
		},
	},
};
</script>
