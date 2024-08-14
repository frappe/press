<template>
	<div class="mx-auto max-w-2xl rounded-lg border-0 px-2 sm:border sm:p-8">
		<div class="prose prose-sm max-w-none">
			<h1 class="text-2xl font-semibold">Welcome to Frappe Cloud</h1>
			<p>
				Frappe Cloud makes it easy to manage sites and apps like ERPNext in an
				easy to use dashboard with powerful features like automatic backups,
				custom domains, SSL certificates, custom apps, automatic updates and
				more.
			</p>
		</div>
		<div class="mt-6 space-y-6">
			<div class="flex items-center space-x-2">
				<div class="text-base font-medium">
					Choose an app below to create your first site.
				</div>
			</div>
			<!-- App Chooser -->
			<div
				v-if="$resources.availableApps.data"
				class="mt-4 grid grid-cols-1 gap-2"
			>
				<div v-for="app in $resources.availableApps.data">
					<a
						:href="`/dashboard/install-app/${app.name}`"
						class="focus:shadow-outline group flex cursor-pointer justify-start rounded-lg border p-2 no-underline transition hover:bg-gray-50"
					>
						<img :src="app.image" class="mr-4 h-12 w-12 rounded-md border" />
						<div>
							<span class="text-base font-semibold">{{ app.title }}</span>
							<p class="mt-1 line-clamp-1 text-sm text-gray-600">
								{{ app.description }}
							</p>
						</div>
					</a>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'Onboarding',
	mounted() {
		if (window.posthog?.__loaded) {
			window.posthog.identify(this.$team.doc.user, {
				app: 'frappe_cloud',
				action: 'onboarding'
			});
			window.posthog.startSessionRecording();
		}
	},
	resources: {
		availableApps() {
			return {
				url: 'press.api.marketplace.get_marketplace_apps_for_onboarding',
				auto: true
			};
		}
	}
};
</script>
