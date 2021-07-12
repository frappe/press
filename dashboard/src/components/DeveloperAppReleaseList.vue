<template>
	<Card title="Your App Releases" subtitle="Created each time you push to GitHub">
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
				<a class="hidden md:inline text-blue-600 font-bold" href="#">
					{{ release.hash.slice(0, 6) }}
				</a>
				<span class="hidden md:inline text-gray-600">
					{{ release.author }}
				</span>
				<span>
					<Badge
						:status="
							release.status || (Math.random() > 0.5 ? 'Draft' : 'Published')
						"
					></Badge>
				</span>
				<span v-if="Math.random() > 0.5">
					<Button type="primary">Publish</Button>
				</span>
				<span v-else-if="Math.random() > 0.7">
					<Button type="secondary">Cancel</Button>
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
