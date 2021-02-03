<template>
	<div>
		<Section title="Apps" description="Apps installed on your site">
			<SectionCard>
				<div
					class="flex px-6 py-3 text-base hover:bg-gray-50 items-center"
					v-for="app in site.installed_apps"
					:key="app.repository_url"
				>
					<div class="flex-1">
						<a
							:href="`${app.repository_url}/tree/${app.branch}`"
							target="_blank"
						>
							<p class="text-base font-medium text-brand">
								{{ app.title }}
							</p>
							<p class="text-sm text-gray-800">
								{{ app.repository_owner }}:{{ app.branch }}
							</p>
						</a>
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
					class="flex px-6 py-3 text-base hover:bg-gray-50 items-center"
					v-for="app in site.available_apps"
					:key="app.repository_url"
				>
					<div class="flex-1">
						<a
							:href="`${app.repository_url}/tree/${app.branch}`"
							target="_blank"
						>
							<p class="text-base font-medium text-brand">
								{{ app.title }}
							</p>
							<p class="text-sm text-gray-800">
								{{ app.repository_owner }}:{{ app.branch }}
							</p>
						</a>
					</div>
					<div>
						<Button @click="installApp(app.app)">
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
			this.$router.push(`/sites/${this.site.name}/general`);
		},
		async uninstallApp(app) {
			await this.$call('press.api.site.uninstall_app', {
				name: this.site.name,
				app: app
			});
			this.$router.push(`/sites/${this.site.name}/general`);
		}
	}
};
</script>
