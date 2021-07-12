<template>
	<div class="bg-white shadow overflow-hidden sm:rounded-md">
		<ul class="divide-y divide-gray-200">
			<li v-for="release in releasesList" :key="release.hash">
				<div href="#" class="block">
					<div class="px-4 py-4 sm:px-6">
						<div class="flex items-center justify-between">
							<p class="text-base font-medium text-blue-600 truncate max-w-md">
								{{ release.message }}
							</p>
							<div class="ml-2 flex-shrink-0 flex">
								<Badge :status="release.status || 'Draft'" />
							</div>
							<Button
								v-if="release.status != 'Awaiting Approval'"
								type="primary"
								:disabled="
									['Published', 'Rejected'].includes(release.status) ||
										release.author == 'Faris'
								"
								>Publish</Button
							>
							<Button v-else type="secondary">Cancel</Button>
						</div>
						<div class="mt-2 sm:flex sm:justify-between">
							<div class="sm:flex">
								<a
									href="#"
									class="flex items-center text-sm text-blue-500 font-semibold"
								>
									{{ release.hash.slice(0, 6) }}
								</a>
								<p
									class="mt-2 flex items-center text-sm text-gray-500 sm:mt-0 sm:ml-6"
								>
									by
									{{ release.author }}
								</p>
							</div>
							<div class="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
								<p>
									{{ ' ' }}
									<time :datetime="release.creation">{{
										release.creation
									}}</time>
								</p>
							</div>
						</div>
					</div>
				</div>
			</li>
		</ul>
	</div>
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
		}
	},
	computed: {
		releasesList() {
			if (!this.$resources.releases.data || this.$resources.releases.loading) {
				return [];
			}

			return this.$resources.releases.data;
		}
	}
};
</script>
