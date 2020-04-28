<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Apps</h2>
			<p class="text-gray-600">Apps installed on your site</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded shadow sm:w-1/2"
			>
				<div
					class="flex px-6 py-3 hover:bg-gray-50"
					v-for="app in site.installed_apps"
					:key="app.url"
				>
					<div class="flex-1 my-auto text-md">
						<p>
							{{ app.name }}
						</p>
					</div>
					<div class="flex-1 text-md">
						<a :href="`${app.url}/tree/${app.branch}`" target="_blank">
							<p class="font-medium text-brand">
								{{ app.owner }}/{{ app.repo }}
							</p>
							<p class="text-sm text-gray-800">
								{{ app.branch }}
							</p>
						</a>
					</div>
					<div class="flex-1 text-md"></div>
				</div>
			</div>
		</section>
		<section class="mt-10" v-if="site.available_apps.length">
			<h2 class="text-lg font-medium">Available Apps</h2>
			<p class="text-gray-600">Apps available to install on your site</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded shadow sm:w-1/2"
			>
				<div
					class="flex px-6 py-3 hover:bg-gray-50"
					v-for="app in site.available_apps"
					:key="app.url"
				>
					<div class="flex-1 my-auto text-md">
						<p>
							{{ app.name }}
						</p>
					</div>
					<div class="flex-1 text-md">
						<a :href="`${app.url}/tree/${app.branch}`" target="_blank">
							<p class="font-medium text-brand">
								{{ app.owner }}/{{ app.repo }}
							</p>
							<p class="text-sm text-gray-800">
								{{ app.branch }}
							</p>
						</a>
					</div>
					<div class="flex-1 text-md">
						<Button @click="installApp(app.name)">
							Install
						</Button>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteApps',
	props: ['site'],
	methods: {
		async installApp(app) {
			await this.$call('press.api.site.install_app', {
				name: this.site.name,
				app: app
			});
			this.$parent.$store.sites.fetchSite(this.site.name);
		}
	}
};
</script>
