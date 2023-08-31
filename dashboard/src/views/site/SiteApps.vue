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
				:disabled="site?.status === 'Suspended'"
			>
				Add App
			</Button>
		</template>

		<LoadingText v-if="$resources.installedApps.loading" />
		<div v-else class="divide-y">
			<div
				class="flex items-center py-3"
				v-for="app in $resources.installedApps.data"
				:key="app.name"
			>
				<div class="w-2/3">
					<div class="flex flex-row items-center">
						<div class="text-lg font-medium text-gray-900">
							{{ app.title }}
						</div>

						<CommitTag
							class="ml-2"
							:tag="app.tag || app.hash.substr(0, 7)"
							:link="`${app.repository_url}/commit/${app.hash}`"
						/>
					</div>

					<div class="mt-[2px] text-base text-gray-600">
						{{ app.repository_owner }}/{{ app.repository }}:{{ app.branch }}
					</div>
				</div>
				<div class="ml-auto flex items-center space-x-2">
					<Dropdown :options="dropdownItems(app)" right>
						<template v-slot="{ open }">
							<Button icon="more-horizontal" />
						</template>
					</Dropdown>
				</div>
			</div>
		</div>

		<Dialog
			:options="{ title: 'Install an app on your site' }"
			v-model="showInstallAppsDialog"
		>
			<template v-slot:body-content>
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
							:loading="
								$resources.installApp.loading && appToInstall.name == app.name
							"
						>
							Install
						</Button>
					</div>
				</div>
				<div class="text-base text-gray-600" v-else>
					No apps available to install
				</div>

				<div v-if="site?.group">
					<p class="mt-4 text-sm text-gray-700">
						<Link :to="`/benches/${site.group}/apps`" class="font-medium">
							Add more apps to your bench
						</Link>
					</p>
				</div>
			</template>
		</Dialog>

		<Dialog
			v-model="showCheckoutDialog"
			title="Checkout Details"
			:dismissable="true"
		>
			<MarketplacePrepaidCredits
				v-if="selectedPlan"
				:app="appToInstall.app"
				:site="site.name"
				:plan="selectedPlan"
			/>
		</Dialog>

		<Dialog
			v-model="showPlanSelectionDialog"
			title="Select app plan"
			width="half"
			:dismissable="true"
		>
			<ChangeAppPlanSelector
				v-if="appToInstall?.app"
				:app="appToInstall.app"
				:frappeVersion="site?.frappe_version"
				:editable="false"
				class="mb-9"
				@change="
					plan => {
						selectedPlan = plan.name;
						selectedPlanIsFree = plan.is_free;
					}
				"
			/>

			<ErrorMessage :message="$resourceErrors" />

			<template #actions>
				<Button
					appearance="primary"
					:loading="$resources.installApp.loading"
					@click="handlePlanSelection"
					>Proceed</Button
				>
			</template>
		</Dialog>
	</Card>
	<SiteOverviewAppSubscriptions class="mt-4 md:col-span-2" :site="site" />
</template>
<script>
import CommitTag from '@/components/utils/CommitTag.vue';
import ChangeAppPlanSelector from '@/components/ChangeAppPlanSelector.vue';
import SiteOverviewAppSubscriptions from './SiteOverviewAppSubscriptions.vue';
import MarketplacePrepaidCredits from '../marketplace/MarketplacePrepaidCredits.vue';

export default {
	name: 'SiteOverviewApps',
	props: ['site'],
	data() {
		return {
			showInstallAppsDialog: false,
			showPlanSelectionDialog: false,
			showCheckoutDialog: false,
			appToInstall: null,
			selectedPlan: null,
			selectedPlanIsFree: null
		};
	},
	components: {
		ChangeAppPlanSelector,
		CommitTag,
		SiteOverviewAppSubscriptions,
		MarketplacePrepaidCredits
	},
	resources: {
		installedApps() {
			return {
				url: 'press.api.site.installed_apps',
				params: { name: this.site?.name },
				auto: true
			};
		},
		availableApps() {
			return {
				url: 'press.api.site.available_apps',
				params: { name: this.site?.name }
			};
		},
		installApp() {
			return {
				url: 'press.api.site.install_app',
				params: {
					name: this.site?.name,
					app: this.appToInstall?.app,
					plan: this.selectedPlan
				},
				validate() {
					if (this.showPlanSelectionDialog && !this.selectedPlan) {
						return 'Please select a plan to continue';
					}
				},
				onSuccess() {
					this.showPlanSelectionDialog = false;
					this.showInstallAppsDialog = false;
					this.$emit('app-installed');
				}
			};
		},
		uninstallApp: {
			url: 'press.api.site.uninstall_app',
			onSuccess() {
				this.$emit('app-uninstalled');
			}
		}
	},
	computed: {
		availableApps() {
			return this.$resources.availableApps;
		}
	},
	methods: {
		installApp(app) {
			this.appToInstall = app;

			// If paid app, show plan selection dialog
			if (app.has_plans_available) {
				this.showInstallAppsDialog = false;
				this.showPlanSelectionDialog = true;
				return;
			}

			this.$resources.installApp.submit({
				name: this.site?.name,
				app: this.appToInstall?.app,
				plan: this.selectedPlan
			});
		},
		handlePlanSelection() {
			if (
				this.appToInstall.billing_type == 'prepaid' &&
				!this.selectedPlanIsFree
			) {
				if (this.$account.hasBillingInfo) {
					this.showPlanSelectionDialog = false;
					this.showCheckoutDialog = true;
				} else {
					window.location = '/dashboard/billing';
				}
			} else {
				this.$resources.installApp.submit();
			}
		},
		dropdownItems(app) {
			return [
				app.app != 'frappe' && {
					label: 'Remove App',
					handler: () => this.confirmRemoveApp(app)
				},
				{
					label: 'Visit Repo',
					handler: () =>
						window.open(`${app.repository_url}/tree/${app.branch}`, '_blank')
				}
			].filter(Boolean);
		},
		confirmRemoveApp(app) {
			this.$confirm({
				title: 'Remove App',
				message: `Are you sure you want to uninstall app ${app.title} from site?`,
				actionLabel: 'Remove App',
				actionColor: 'red',
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
