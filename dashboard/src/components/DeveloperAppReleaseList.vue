<template>
	<Card
		title="Your App Releases"
		subtitle="Created each time you push to GitHub"
	>
		<div class="divide-y">
			<div
				class="grid items-center grid-cols-3 py-4 text-base text-gray-600 gap-x-8 md:grid-cols-6"
			>
				<span class="md:col-span-2">Commit Message</span>
				<span class="hidden md:inline">Hash</span>
				<span class="hidden md:inline">Author</span>
				<span>Status</span>
				<span></span>
			</div>

			<div
				v-for="release in releasesList"
				:key="release.name"
				class="grid items-center grid-cols-3 py-4 text-base text-gray-900 gap-x-8 md:grid-cols-6"
			>
				<p
					class="md:col-span-2 text-base font-medium text-gray-700 truncate max-w-md"
				>
					{{ release.message }}
				</p>
				<a
					:href="`${release.source.repository_url}/commit/${release.hash}`"
					target="_blank"
					class="hidden md:inline text-blue-700 font-bold hover:text-blue-500"
				>
					{{ release.hash.slice(0, 6) }}
				</a>
				<span class="hidden md:inline text-gray-600">
					{{ release.author }}
				</span>
				<span>
					<Badge :status="release.status"></Badge>
				</span>
				<span
					v-if="
						release.status == 'Draft' &&
							$date(release.creation) > latestPublishedOn
					"
				>
					<Button
						:loading="$resources.createApprovalRequest.loading"
						type="primary"
						@click="createApprovalRequest(release.name)"
						>Publish</Button
					>
				</span>
				<span v-else-if="release.status == 'Awaiting Approval'">
					<Button type="secondary" @click="cancelApprovalRequest(release.name)"
						>Cancel</Button
					>
				</span>
				<span v-else></span>
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
	resources: {
		releases() {
			let { app } = this.app;
			return {
				method: 'press.api.developer.releases',
				params: {
					app: 'frappe' // TODO: Change after testing
				},
				auto: true
			};
		},
		latestPublished() {
			return {
				method: 'press.api.developer.latest_published_release',
				params: {
					app: 'frappe' // TODO: Change after testing
				},
				auto: true
			};
		},
		createApprovalRequest() {
			return {
				method: 'press.api.developer.create_approval_request',
				onSuccess() {
					this.$resources.releases.submit();
				}
			};
		},
		cancelApprovalRequest() {
			return {
				method: 'press.api.developer.cancel_approval_request',
				onSuccess() {
					this.$resources.releases.submit();
				}
			};
		}
	},
	methods: {
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
		}
	},
	computed: {
		releasesList() {
			if (!this.$resources.releases.data || this.$resources.releases.loading) {
				return [];
			}

			return this.$resources.releases.data;
		},

		latestPublishedOn() {
			if (
				this.$resources.latestPublished.data &&
				!this.$resources.latestPublished.loading
			) {
				return this.$date(this.$resources.latestPublished.data.creation);
			}
		}
	}
};
</script>
