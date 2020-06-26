<template>
	<div>
		<Section title="Apps" description="Apps installed on your site">
			<SectionCard>
				<div
					class="flex px-6 py-3 text-base hover:bg-gray-50"
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
					<div v-if="!app.frappe">
						<Button @click="uninstallApp(app.name)">
							Uninstall
						</Button>
					</div>
				</div>
			</SectionCard>
		</Section>
		<Section
			title="Available Apps"
			description="Apps available to install on your site"
			class="mt-10"
			v-if="site.available_apps.length"
		>
			<SectionCard>
				<div
					class="flex px-6 py-3 text-base hover:bg-gray-50"
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
			</SectionCard>
		</Section>
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
		},
		async uninstallApp(app) {
			await this.$call('press.api.site.uninstall_app', {
				name: this.site.name,
				app: app
			});
		}
	}
};
</script>
