<template>
	<Card title="Apps" subtitle="Apps installed on your site">
		<template #actions>
			<Button
				icon-left="plus"
				@click="
					() => {
						showInstallAppsDialog = true;
						$resources.availableApps.fetch();
					}
				"
			>
				Add App
			</Button>
		</template>
		<div class="divide-y">
			<div class="flex py-3" v-for="app in installedApps" :key="app.name">
				<div class="w-1/3 text-base font-medium">
					{{ app.owner }}/{{ app.repo }}
				</div>
				<div class="text-base text-gray-700">
					{{ app.branch }}
				</div>
				<Link
					:href="`${app.url}/tree/${app.branch}`"
					target="_blank"
					class="inline-flex ml-auto text-base"
				>
					Visit Repo →
				</Link>
			</div>
		</div>

		<Dialog title="Install an app on your site" v-model="showInstallAppsDialog">
			<div class="divide-y">
				<div
					class="flex items-center py-3"
					v-for="app in availableApps.data"
					:key="app.name"
				>
					<div class="w-1/3 text-base font-medium">
						{{ app.owner }}/{{ app.repo }}
					</div>
					<div class="text-base text-gray-700">
						{{ app.branch }}
					</div>
					<Button
						class="ml-auto"
						@click="installApp(app.name)"
						:loading="$resources.installApp.loading && appToInstall == app.name"
					>
						Install
					</Button>
				</div>
			</div>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'SiteOverviewApps',
	props: ['site', 'installedApps'],
	data() {
		return {
			showInstallAppsDialog: false,
			appToInstall: null
		};
	},
	resources: {
		availableApps() {
			return {
				method: 'press.api.site.available_apps',
				params: { name: this.site.name }
			};
		},
		installApp() {
			return {
				method: 'press.api.site.install_app',
				params: {
					name: this.site.name,
					app: this.appToInstall
				},
				onSuccess() {
					this.showInstallAppsDialog = false;
					this.$emit('app-installed');
				}
			};
		}
	},
	methods: {
		installApp(app) {
			this.appToInstall = app;
			this.$resources.installApp.submit();
		}
	}
};
</script>
