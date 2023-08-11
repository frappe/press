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

		<div class="flex text-base text-gray-600">
			<span class="w-2/6">App</span>
			<span class="hidden w-1/6 md:inline">Plan</span>
			<span class="w-1/6">Status</span>
			<span class="hidden w-1/6 md:inline">Price</span>
			<span></span>
		</div>

		<LoadingText v-if="$resources.installedApps.loading" />

		<div v-else class="divide-y">
			<div
				class="flex items-center py-4 text-base text-gray-600"
				v-for="app in $resources.installedApps.data"
				:key="app.name"
			>
				<div class="w-2/6">
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

					<div
						class="mt-[2px] truncate text-base text-gray-600 hover:text-clip"
					>
						{{ app.repository_owner }}/{{ app.repository }}:{{ app.branch }}
					</div>
				</div>

				<div class="w-1/6">
					<span v-if="app.subscription.plan">
						{{ app.subscription.plan }}
					</span>
					<span v-else>-</span>
				</div>

				<div class="w-1/6">
					<span v-if="app.subscription.status"
						><Badge :label="app.subscription.status" />
					</span>
					<span v-else>-</span>
				</div>

				<div class="w-1/6">
					<span v-if="app.plan_info">
						{{ app.is_free ? 'Free' : $planTitle(app.plan_info) }}
					</span>
					<span v-else>-</span>
				</div>

				<div class="ml-auto flex items-center space-x-2">
					<Button v-if="app.plan_info" @click="changeAppPlan(app)"
						>Change Plan</Button
					>
					<Button
						v-if="!app.plan_info && app.subscription_available"
						@click="
							() => {
								showPlanSelectionDialog = true;
								appToInstall = app;
							}
						"
						>Subscribe</Button
					>
					<Dropdown :options="dropdownItems(app)" right>
						<template v-slot="{ open }">
							<Button icon="more-horizontal" />
						</template>
					</Dropdown>
				</div>
			</div>
		</div>

		<Dialog
			:options="{
				title: 'Install an app on your site',
				position: 'top',
				size: 'lg'
			}"
			v-model="showInstallAppsDialog"
		>
			<template v-slot:body-content>
				<FormControl
					class="mb-2"
					placeholder="Search for Apps"
					v-on:input="e => updateSearchTerm(e)"
				/>
				<div
					v-if="availableApps.data && availableApps.data.length"
					class="max-h-96 divide-y overflow-auto"
					:class="filteredOptions.length > 7 ? 'pr-2' : ''"
				>
					<div
						class="flex items-center py-3"
						v-for="app in filteredOptions"
						:key="app.name"
					>
						<div class="w-2/4 text-base font-medium">
							{{ app.title }}
						</div>
						<div class="w-1/4 text-base text-gray-700">
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

		<!-- New App Install -->
		<Dialog
			v-model="showPlanSelectionDialog"
			:options="{
				title: 'Select app plan',
				size: '2xl',
				actions: [
					{
						label: 'Proceed',
						variant: 'solid',
						onClick: handlePlanSelection
					}
				]
			}"
		>
			<template v-slot:body-content>
				<ChangeAppPlanSelector
					v-if="appToInstall?.app"
					:app="appToInstall.app"
					:frappeVersion="site?.frappe_version"
					class="mb-9"
					@change="
						plan => {
							selectedPlan = plan.name;
							selectedPlanIsFree = plan.is_free;
						}
					"
				/>

				<ErrorMessage :message="$resourceErrors" />
			</template>
		</Dialog>

		<!-- Plan Change Dialog -->
		<Dialog
			:options="{
				title: 'Select Plan',
				size: '2xl',
				actions: [
					{
						label: 'Change Plan',
						variant: 'solid',
						onClick: handlePlanChange,
						loading: $resources.changePlan.loading
					}
				]
			}"
			v-model="showAppPlanChangeDialog"
		>
			<template v-slot:body-content>
				<ChangeAppPlanSelector
					@change="
						plan => {
							newAppPlan = plan.name;
							newAppPlanIsFree = plan.is_free;
						}
					"
					v-if="appToChangePlan"
					:app="appToChangePlan.name"
					:currentPlan="appToChangePlan.plan"
					:frappeVersion="site.frappe_version"
				/>
			</template>
		</Dialog>

		<Dialog
			v-model="showCheckoutDialog"
			:options="{ title: 'Checkout Details' }"
			:dismissable="true"
		>
			<template v-slot:body-content>
				<MarketplacePrepaidCredits
					v-if="newAppPlan"
					:subscription="currentSubscription"
					:app="appToChangePlan.name"
					:appTitle="appToChangePlan.title"
					:site="site.name"
					:plan="newAppPlan"
				/>

				<MarketplacePrepaidCredits
					v-if="selectedPlan"
					:app="appToInstall.app"
					:appTitle="appToInstall.title"
					:site="site.name"
					:plan="selectedPlan"
				/>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import CommitTag from '@/components/utils/CommitTag.vue';
import ChangeAppPlanSelector from '@/components/ChangeAppPlanSelector.vue';
import SiteOverviewAppSubscriptions from './SiteOverviewAppSubscriptions.vue';
import MarketplacePrepaidCredits from '../marketplace/MarketplacePrepaidCredits.vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'SiteOverviewApps',
	props: ['site'],
	data() {
		return {
			showInstallAppsDialog: false,
			showPlanSelectionDialog: false,
			showAppPlanChangeDialog: false,
			showCheckoutDialog: false,
			appToChangePlan: null,
			newAppPlan: '',
			appToInstall: null,
			selectedPlan: null,
			selectedPlanIsFree: null,
			searchTerm: '',
			filteredOptions: []
		};
	},
	components: {
		ChangeAppPlanSelector,
		CommitTag,
		SiteOverviewAppSubscriptions,
		MarketplacePrepaidCredits
	},
	resources: {
		marketplaceSubscriptions() {
			return {
				method: 'press.api.marketplace.get_marketplace_subscriptions_for_site',
				params: {
					site: this.site?.name
				},
				auto: true
			};
		},

		changePlan() {
			return {
				method: 'press.api.marketplace.change_app_plan',
				onSuccess() {
					this.showAppPlanChangeDialog = false;
					this.$resources.marketplaceSubscriptions.fetch();
				},
				onError(e) {
					this.showAppPlanChangeDialog = false;
					this.$notify({
						title: e,
						color: 'red',
						icon: 'x'
					});
				}
			};
		},

		installedApps() {
			return {
				method: 'press.api.site.installed_apps',
				params: { name: this.site?.name },
				auto: true
			};
		},

		availableApps() {
			return {
				method: 'press.api.site.available_apps',
				params: { name: this.site?.name }
			};
		},

		installApp() {
			return {
				method: 'press.api.site.install_app',
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
			method: 'press.api.site.uninstall_app',
			onSuccess() {
				this.$emit('app-uninstalled');
			}
		}
	},
	computed: {
		availableApps() {
			if (this.$resources.availableApps.data) {
				this.fuse = new Fuse(this.$resources.availableApps.data, {
					limit: 20,
					keys: ['title']
				});
				this.filteredOptions = this.$resources.availableApps.data;
			}
			return this.$resources.availableApps;
		},
		marketplaceSubscriptions() {
			if (
				this.$resources.marketplaceSubscriptions.data &&
				!this.$resources.marketplaceSubscriptions.loading
			) {
				return this.$resources.marketplaceSubscriptions.data;
			}

			return [];
		}
	},
	methods: {
		updateSearchTerm(value) {
			if (value) {
				this.filteredOptions = this.fuse
					.search(value)
					.map(result => result.item);
			} else {
				this.filteredOptions = this.$resources.availableApps.data;
			}
		},
		subscribe(app) {
			this.showPlanSelectionDialog = true;
		},

		changeAppPlan(app) {
			this.currentSubscription = app.subscription.name;
			this.currentAppPlan = app.subscription.marketplace_app_plan;
			this.newAppPlan = this.currentAppPlan;

			this.appToChangePlan = {
				name: app.subscription.app,
				title: app.app_title,
				image: app.app_image,
				plan: app.subscription.marketplace_app_plan,
				subscription: app.subscription.name,
				billing_type: app.billing_type
			};
			this.showAppPlanChangeDialog = true;
		},

		handlePlanChange() {
			if (
				this.appToChangePlan.billing_type == 'prepaid' &&
				!this.newAppPlanIsFree
			) {
				if (this.$account.hasBillingInfo) {
					this.showAppPlanChangeDialog = false;
					this.showCheckoutDialog = true;
				} else {
					window.location = '/dashboard/billing';
				}
			} else {
				this.switchToNewPlan();
			}
		},

		switchToNewPlan() {
			if (this.currentAppPlan !== this.newAppPlan) {
				this.$resources.changePlan.submit({
					subscription: this.appToChangePlan.subscription,
					new_plan: this.newAppPlan
				});
			} else {
				this.showAppPlanChangeDialog = false;
			}
		},
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
					onClick: () => this.confirmRemoveApp(app)
				},
				{
					label: 'Visit Repo',
					onClick: () =>
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
