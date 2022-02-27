<template>
	<Card title="Apps" subtitle="Apps installed on your site">
		<template #actions>
			<Button
				@click="
					() => {
						showInstallAppsDialog = true;
						$resources.availableApps.fetch();
					}
				"
				:disabled="site.status === 'Suspended'"
			>
				Add App
			</Button>
		</template>
		<div class="divide-y">
			<div
				class="flex items-center py-3"
				v-for="app in installedApps"
				:key="app.name"
			>
				<div class="w-2/3">
					<div class="text-base font-medium">
						{{ app.title }}
					</div>
					<div class="mt-1 text-base text-gray-700">
						{{ app.repository_owner }}/{{ app.repository }}:{{ app.branch }}
					</div>
				</div>
				<div class="ml-auto flex items-center space-x-2">
					<a
						class="block cursor-pointer"
						:href="`${app.repository_url}/commit/${app.hash}`"
						target="_blank"
					>
						<Badge class="cursor-pointer hover:text-blue-500" color="blue">
							{{ app.tag || app.hash.substr(0, 7) }}
						</Badge>
					</a>
					<Dropdown :items="dropdownItems(app)" right>
						<template v-slot="{ toggleDropdown }">
							<Button icon="more-horizontal" @click="toggleDropdown()" />
						</template>
					</Dropdown>
				</div>
			</div>
		</div>

		<Dialog title="Install an app on your site" v-model="showInstallAppsDialog">
			<div
				v-if="availableApps.data && availableApps.data.length"
				class="divide-y"
			>
				<div
					class="flex items-center py-3"
					v-for="app in availableApps.data"
					:key="app.name"
				>
					<div class="w-1/3 text-base font-medium">
						{{ app.title }}
					</div>
					<div class="text-base text-gray-700">
						{{ app.repository_owner }}:{{ app.branch }}
					</div>
					<Button
						class="ml-auto"
						@click="installApp(app)"
						:loading="$resources.installApp.loading && appToInstall == app.name"
					>
						Install
					</Button>
				</div>
			</div>
			<div class="text-base text-gray-600" v-else>
				No apps available to install
			</div>
		</Dialog>

		<Dialog
			v-model="showPlanSelectionDialog"
			title="Select app plan"
			width="half"
			:dismissable="true"
		>
			<ChangeAppPlanSelector
				:app="appToInstall"
				:frappeVersion="site.frappe_version"
				class="mb-9"
				@change="plan => (selectedPlan = plan.name)"
			/>

			<template #actions>
				<Button
					type="primary"
					:loading="$resources.installApp.loading"
					@click="$resources.installApp.submit()"
					>Proceed</Button
				>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import ChangeAppPlanSelector from '@/components/ChangeAppPlanSelector.vue';

export default {
	name: 'SiteOverviewApps',
	props: ['site', 'installedApps'],
	data() {
		return {
			showInstallAppsDialog: false,
			showPlanSelectionDialog: false,
			appToInstall: null,
			selectedPlan: null
		};
	},
	components: { ChangeAppPlanSelector },
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
					app: this.appToInstall,
					plan: this.selectedPlan
				},
				onSuccess() {
					this.showPlanSelectionDialog = false;
					this.showInstallAppsDialog = false;
					this.$emit('app-installed');
				}
			};
		},
		uninstallApp: {
			method: 'press.api.site.uninstall_app',
			onSuccess() {
				this.$emit('app-uninstalled');
			}
		}
	},
	methods: {
		installApp(app) {
			this.appToInstall = app.app;

			// If paid app, show plan selection dialog
			if (app.has_plans_available) {
				this.showInstallAppsDialog = false;
				this.showPlanSelectionDialog = true;
				return;
			}

			this.$resources.installApp.submit();
		},
		dropdownItems(app) {
			return [
				app.app != 'frappe' && {
					label: 'Remove App',
					action: () => this.confirmRemoveApp(app)
				},
				{
					label: 'Visit Repo',
					action: () =>
						window.open(`${app.repository_url}/tree/${app.branch}`, '_blank')
				}
			].filter(Boolean);
		},
		confirmRemoveApp(app) {
			this.$confirm({
				title: 'Remove App',
				message: `Are you sure you want to uninstall app ${app.title} from site?`,
				actionLabel: 'Remove App',
				actionType: 'danger',
				action: closeDialog => {
					closeDialog();
					this.$resources.uninstallApp.submit({
						name: this.site.name,
						app: app.app
					});
				}
			});
		}
	}
};
</script>
