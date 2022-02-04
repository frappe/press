<template>
	<Card title="App Releases">
		<div v-if="sources.length">
			<div class="flex flex-row items-baseline">
				<select
					v-if="sources.length > 1"
					class="form-select mb-2 inline-block"
					v-model="selectedSource"
				>
					<option
						v-for="source in sources"
						:key="source.source"
						:value="source.source"
					>
						{{
							`${source.source_information.repository}:${source.source_information.branch}`
						}}
					</option>
				</select>
			</div>
		</div>
		<div v-if="!sources.length">
			<p class="mt-3 text-center text-lg text-gray-600">
				No published source exist for this app. Please contact support to
				publish a version of this app.
			</p>
		</div>
		<div v-else-if="releasesList.length === 0 && !$resources.releases.loading">
			<p class="mt-3 text-center text-lg text-gray-600">
				No app releases have been created for this version.
			</p>
		</div>

		<div v-else>
			<div class="divide-y">
				<div
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-600 md:grid-cols-6"
				>
					<span class="md:col-span-2">Commit Message</span>
					<span class="hidden md:inline">Tag</span>
					<span class="hidden md:inline">Author</span>
					<span>Status</span>
					<span></span>
				</div>

				<div
					v-for="release in releasesList"
					:key="release.name"
					class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-900 md:grid-cols-6"
				>
					<p
						class="max-w-md truncate text-base font-medium text-gray-700 md:col-span-2"
					>
						{{ release.message }}
					</p>
					<a
						:href="getCommitUrl(release.hash)"
						target="_blank"
						class="hidden font-mono text-blue-700 hover:text-blue-500 md:inline"
					>
						{{ release.tag || release.hash.slice(0, 6) }}
					</a>
					<span class="hidden text-gray-600 md:inline">
						{{ release.author }}
					</span>
					<span>
						<Badge
							v-if="release.status != 'Draft'"
							:status="release.status"
						></Badge>
					</span>
					<span class="text-right">
						<Button
							v-if="isPublishable(release)"
							:loading="
								$resources.createApprovalRequest.loading ||
								$resources.latestApproved.loading
							"
							type="secondary"
							@click="confirmApprovalRequest(release.name)"
						>
							Publish
						</Button>

						<Button
							v-else-if="release.status == 'Awaiting Approval'"
							type="secondary"
							@click="confirmCancelRequest(release.name)"
							>Cancel</Button
						>

						<Button
							v-else-if="release.status == 'Rejected'"
							type="secondary"
							@click="showFeedback(release)"
							>View Feedback</Button
						>
					</span>
				</div>
				<Dialog
					title="Reason for Rejection"
					:dismissable="true"
					v-model="showRejectionFeedbackDialog"
				>
					<div class="prose text-lg" v-html="rejectionFeedback"></div>
				</Dialog>

				<div class="py-3">
					<Button
						@click="
							pageStart += 15;
							$resources.releases.fetch();
						"
						v-if="!$resources.releases.lastPageEmpty"
						:loading="$resources.releases.loading"
						loadingText="Loading..."
						>Load More</Button
					>
				</div>
			</div>
		</div>
	</Card>
</template>

<script>
export default {
	props: {
		app: {
			type: Object
		}
	},
	data() {
		return {
			pageStart: 0,
			showRejectionFeedbackDialog: false,
			rejectionFeedback: '',
			selectedSource: null
		};
	},
	created() {
		if (this.sources.length > 0) {
			this.selectedSource = this.sources[0].source;
		}
	},
	mounted() {
		this.$socket.on('new_app_release_created', this.releaseStateUpdate);
		this.$socket.on('request_status_changed', this.releaseStateUpdate);
	},
	resources: {
		releases() {
			let { app } = this.app;
			return {
				method: 'press.api.marketplace.releases',
				params: {
					app,
					start: this.pageStart,
					source: this.selectedSource
				},
				paged: true,
				keepData: true
			};
		},
		appSource() {
			return {
				method: 'press.api.marketplace.get_app_source',
				params: {
					name: this.selectedSource
				}
			};
		},
		latestApproved() {
			return {
				method: 'press.api.marketplace.latest_approved_release',
				params: {
					source: this.selectedSource
				},
				auto: true
			};
		},
		createApprovalRequest() {
			return {
				method: 'press.api.marketplace.create_approval_request',
				onSuccess() {
					this.resetReleaseListState();
				},
				onError() {
					this.showRequestError();
				}
			};
		},
		cancelApprovalRequest() {
			return {
				method: 'press.api.marketplace.cancel_approval_request',
				onSuccess() {
					this.resetReleaseListState();
				}
			};
		}
	},
	methods: {
		isPublishable(release) {
			return (
				release.status == 'Draft' &&
				(!this.latestApprovedOn ||
					this.$date(release.creation) > this.latestApprovedOn)
			);
		},
		createApprovalRequest(appRelease) {
			let { app } = this.app;
			this.$resources.createApprovalRequest.submit({
				marketplace_app: app,
				app_release: appRelease
			});
		},
		cancelApprovalRequest(appRelease) {
			let { app } = this.app;
			this.$resources.cancelApprovalRequest.submit({
				marketplace_app: app,
				app_release: appRelease
			});
		},
		resetReleaseListState() {
			this.pageStart = 0;
			this.$resources.releases.reset();
			this.$resources.releases.submit();

			// Re-fetch latest approved
			this.$resources.latestApproved.fetch();
		},
		showFeedback(appRelease) {
			this.showRejectionFeedbackDialog = true;
			this.rejectionFeedback = appRelease.reason_for_rejection;
		},
		showRequestError() {
			const requestAlreadyExists = this.$resources.createApprovalRequest.error
				.toLowerCase()
				.includes('already awaiting');

			if (requestAlreadyExists) {
				// A request already exists
				this.$confirm({
					title: requestAlreadyExists
						? 'A request already exists'
						: 'An error occured',
					message: requestAlreadyExists
						? 'Please cancel the previous request before creating a new one.'
						: this.$resources.createApprovalRequest.error,
					actionLabel: 'OK',
					actionType: 'primary',
					action: (closeDialog) => {
						closeDialog();
					}
				});
			}
		},
		confirmApprovalRequest(appRelease) {
			this.$confirm({
				title: 'Publish Release',
				message:
					'Are you sure you want to publish this release to marketplace? Upon confirmation, the release will be sent for approval by the review team.',
				actionLabel: 'Publish',
				actionType: 'primary',
				action: (closeDialog) => {
					closeDialog();
					this.createApprovalRequest(appRelease);
				}
			});
		},
		confirmCancelRequest(appRelease) {
			this.$confirm({
				title: 'Cancel Release Approval Request',
				message:
					'Are you sure you want to <strong>cancel</strong> the publish request for this release?',
				actionLabel: 'Proceed',
				actionType: 'danger',
				action: (closeDialog) => {
					closeDialog();
					this.cancelApprovalRequest(appRelease);
				}
			});
		},
		getCommitUrl(releaseHash) {
			return `${this.repoUrl}/commit/${releaseHash}`;
		},
		releaseStateUpdate(data) {
			if (this.selectedSource && data.source == this.selectedSource) {
				this.resetReleaseListState();
			}
		}
	},
	computed: {
		releasesList() {
			if (!this.$resources.releases.data) {
				return [];
			}

			return this.$resources.releases.data;
		},

		latestApprovedOn() {
			if (
				this.$resources.latestApproved.data &&
				!this.$resources.latestApproved.loading
			) {
				return this.$date(this.$resources.latestApproved.data.creation);
			}
		},
		sources() {
			// Return only the unique sources
			let tempArray = [];
			for (let source of this.app.sources) {
				if (!tempArray.find((x) => x.source === source.source)) {
					tempArray.push(source);
				}
			}
			return tempArray;
		},
		repoUrl() {
			if (
				this.$resources.appSource.loading ||
				!this.$resources.appSource.data
			) {
				return '';
			}

			return this.$resources.appSource.data.repository_url;
		}
	},
	watch: {
		selectedSource(value) {
			if (value) {
				this.resetReleaseListState();
				this.$resources.appSource.submit();
			}
		}
	}
};
</script>
