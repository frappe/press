<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs
				:items="[
					{ label: 'Sites', route: { name: 'Sites' } },
					{
						label: site?.host_name || site?.name,
						route: { name: 'SiteOverview', params: { siteName: site?.name } }
					}
				]"
			>
				<template #actions>
					<div class="space-x-2">
						<Button
							v-if="site?.status === 'Active'"
							icon-left="external-link"
							label="Visit Site"
							:link="`https://${site?.name}`"
						/>
						<Dropdown :options="siteActions">
							<template v-slot="{ open }">
								<Button variant="ghost" icon="more-horizontal" />
							</template>
						</Dropdown>
					</div>
				</template>
			</Breadcrumbs>
		</header>
		<div class="p-5" v-if="site">
			<div
				class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
			>
				<div class="flex items-center">
					<h1 class="text-2xl font-bold">
						{{ site.host_name || site.name }}
					</h1>
					<Badge class="ml-4" :label="site.status" />
					<div
						v-if="regionInfo"
						class="ml-2 hidden cursor-default flex-row items-center self-end rounded-md bg-yellow-50 px-3 py-1 text-xs font-medium text-yellow-700 md:flex"
					>
						<img
							v-if="regionInfo.image"
							class="mr-2 h-4"
							:src="regionInfo.image"
							:alt="`Flag of ${regionInfo.title}`"
							:title="regionInfo.image"
						/>
						<p>{{ regionInfo.title }}</p>
					</div>
				</div>
				<Button
					@click="onActivateClick"
					v-if="site.pending_for_long"
					:variant="'solid'"
					class="mr-1"
				>
					Activate
				</Button>
				<div class="mb-10 flex flex-row justify-between md:hidden">
					<div class="flex flex-row">
						<div
							v-if="regionInfo"
							class="flex cursor-default flex-row items-center rounded-md bg-yellow-50 px-3 py-1 text-xs font-medium text-yellow-700"
						>
							<img
								v-if="regionInfo.image"
								class="mr-2 h-4"
								:src="regionInfo.image"
								:alt="`Flag of ${regionInfo.title}`"
								:title="regionInfo.image"
							/>
							<p>{{ regionInfo.title }}</p>
						</div>
					</div>
				</div>
			</div>
			<div class="mb-2 mt-4">
				<SiteAlerts
					v-if="site && $resources.plan?.data && !$resources.site.loading"
					:site="site"
					:plan="$resources.plan.data"
					@plan-change="handlePlanChange"
				/>
			</div>
			<Tabs :tabs="tabs">
				<router-view v-slot="{ Component, route }">
					<component
						v-if="site"
						:is="Component"
						:site="site"
						:plan="$resources.plan.data"
						@plan-change="handlePlanChange"
					/>
				</router-view>
			</Tabs>
		</div>

		<Dialog
			:options="{
				title: 'Login As Administrator',
				actions: [
					{
						label: 'Proceed',
						variant: 'solid',
						onClick: proceedWithLoginAsAdmin
					}
				]
			}"
			v-model="showReasonForAdminLoginDialog"
		>
			<template v-slot:body-content>
				<FormControl
					label="Reason for logging in as Administrator"
					type="textarea"
					v-model="reasonForAdminLogin"
					required
				/>
				<ErrorMessage class="mt-3" :message="errorMessage" />
			</template>
		</Dialog>

		<SiteTransferDialog :site="site" v-model="showTransferSiteDialog" />

		<SiteChangeGroupDialog
			v-if="site"
			:site="site"
			v-model="showChangeGroupDialog"
		/>
		<SiteChangeRegionDialog
			v-if="site"
			:site="site"
			v-model="showChangeRegionDialog"
		/>
		<SiteChangeServerDialog
			v-if="site"
			:site="site"
			v-model="showChangeServerDialog"
		/>
		<SiteVersionUpgradeDialog
			v-if="site"
			:site="site"
			v-model="showVersionUpgradeDialog"
		/>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
import { loginAsAdmin } from '@/controllers/loginAsAdmin';
import SiteAlerts from './SiteAlerts.vue';
import { notify } from '@/utils/toast';
import SiteTransferDialog from './SiteTransferDialog.vue';
import SiteChangeGroupDialog from './SiteChangeGroupDialog.vue';
import SiteChangeRegionDialog from './SiteChangeRegionDialog.vue';
import SiteVersionUpgradeDialog from './SiteVersionUpgradeDialog.vue';
import SiteChangeServerDialog from './SiteChangeServerDialog.vue';

export default {
	name: 'Site',
	pageMeta() {
		return {
			title: `Site - ${this.siteName} - Frappe Cloud`
		};
	},
	props: ['siteName'],
	components: {
		SiteAlerts,
		Tabs,
		SiteTransferDialog,
		SiteChangeGroupDialog,
		SiteChangeRegionDialog,
		SiteChangeServerDialog,
		SiteVersionUpgradeDialog
	},
	data() {
		return {
			runningJob: false,
			reasonForAdminLogin: '',
			showReasonForAdminLoginDialog: false,
			showTransferSiteDialog: false,
			showChangeGroupDialog: false,
			showChangeRegionDialog: false,
			showChangeServerDialog: false,
			showVersionUpgradeDialog: false,
			errorMessage: ''
		};
	},
	resources: {
		site() {
			return {
				url: 'press.api.site.get',
				params: {
					name: this.siteName
				},
				auto: true,
				onSuccess() {
					this.routeToGeneral();

					if (this.siteName !== this.site.name) {
						this.$router.replace({ params: { siteName: this.site.name } });
					}
					if (this.site.status !== 'Active' || this.site.setup_wizard_complete)
						return;

					this.$call('press.api.site.setup_wizard_complete', {
						name: this.siteName
					})
						.then(complete => {
							this.site.setup_wizard_complete = Boolean(complete);
						})
						.catch(() => (this.site.setup_wizard_complete = false));
				},
				onError: this.$routeTo404PageIfNotFound
			};
		},
		loginAsAdmin() {
			return loginAsAdmin(this.siteName);
		},
		plan() {
			return {
				url: 'press.api.site.current_plan',
				params: {
					name: this.siteName
				},
				auto: true
			};
		}
	},
	activated() {
		this.setupAgentJobUpdate();

		if (this.site?.status === 'Active') {
			this.$socket.on('list_update', this.onSocketUpdate);
		}
	},
	deactivated() {
		this.$socket.off('list_update', this.onSocketUpdate);
	},
	methods: {
		onSocketUpdate({ doctype, name }) {
			if (doctype === 'Site' && name === this.siteName) {
				this.$resources.site.reload();
			}
		},
		setupAgentJobUpdate() {
			if (this._agentJobUpdateSet) return;
			this._agentJobUpdateSet = true;

			this.$socket.on('agent_job_update', data => {
				if (data.name === 'New Site' || data.name === 'New Site from Backup') {
					if (data.status === 'Success' && data.site === this.siteName) {
						setTimeout(() => {
							// running reload immediately doesn't work for some reason
							this.$router.push(`/sites/${this.siteName}/overview`);
							this.$resources.site.reload();
						}, 1000);
					}
				}
				this.runningJob =
					data.site === this.siteName && data.status !== 'Success';
			});
		},
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let tab = ['Pending', 'Installing'].includes(this.site?.status)
					? 'jobs'
					: 'overview';
				this.$router.replace(`/sites/${this.site?.name}/${tab}`);
			}
		},
		proceedWithLoginAsAdmin() {
			this.errorMessage = '';

			if (!this.reasonForAdminLogin.trim()) {
				// The input is empty
				this.errorMessage = 'Reason is required';
				return;
			}

			this.$resources.loginAsAdmin.submit({
				name: this.siteName,
				reason: this.reasonForAdminLogin
			});

			this.showReasonForAdminLoginDialog = false;
		},
		handlePlanChange() {
			this.$resources.site.reload();
			this.$resources.plan.reload();
		},
		onActivateClick() {
			this.$confirm({
				title: 'Activate Site',
				message: `Are you sure you want to activate this site?`,
				actionLabel: 'Activate',
				action: () => this.activate()
			});
		},
		activate() {
			this.$call('press.api.site.activate', {
				name: this.site.name
			});
			notify({
				title: 'Site activated successfully!',
				message: 'You can now access your site',
				icon: 'check',
				color: 'green'
			});
			setTimeout(() => window.location.reload(), 1000);
		}
	},
	computed: {
		site() {
			return this.$resources.site.data;
		},

		regionInfo() {
			if (!this.$resources.site.loading && this.$resources.site.data) {
				return this.$resources.site.data.server_region_info;
			}
		},

		siteActions() {
			return [
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$account.user.user_type === 'System User',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/site/${this.site?.name}`,
							'_blank'
						);
					}
				},
				{
					label: 'Manage Bench',
					icon: 'tool',
					route: `/benches/${this.site?.group}`,
					condition: () => this.site?.group,
					onClick: () => {
						this.$router.push(`/benches/${this.site?.group}`);
					}
				},
				{
					label: 'Login As Administrator',
					icon: 'external-link',
					loading: this.$resources.loginAsAdmin.loading,
					condition: () => this.site?.status === 'Active',
					onClick: () => {
						if (this.$account.team.name == this.site?.notify_email) {
							return this.$resources.loginAsAdmin.submit({
								name: this.siteName
							});
						}

						this.showReasonForAdminLoginDialog = true;
					}
				},
				{
					label: 'Impersonate Team',
					icon: 'tool',
					condition: () => this.$account.user.user_type === 'System User',
					onClick: async () => {
						await this.$account.switchTeam(this.site?.team);
						notify({
							title: 'Switched Team',
							message: `Switched to ${this.site?.team}`,
							icon: 'check',
							color: 'green'
						});
					}
				},
				{
					label: 'Transfer Site',
					icon: 'tool',
					condition: () =>
						this.site?.status === 'Active' && !this.$account.parent_team,
					onClick: () => {
						this.showTransferSiteDialog = true;
					}
				},
				{
					label: 'Change Bench',
					icon: 'package',
					condition: () => this.site?.status === 'Active',
					onClick: () => (this.showChangeGroupDialog = true)
				},
				{
					label: 'Change Region',
					icon: 'globe',
					condition: () => this.site?.status === 'Active',
					onClick: () => (this.showChangeRegionDialog = true)
				},
				{
					label: 'Upgrade Version',
					icon: 'arrow-up',
					condition: () => this.site?.status === 'Active',
					onClick: () => (this.showVersionUpgradeDialog = true)
				},
				{
					label: 'Change Server',
					icon: 'server',
					condition: () =>
						this.site?.status === 'Active' && !this.site?.is_public,
					onClick: () => (this.showChangeServerDialog = true)
				}
			];
		},

		hasMonitorAccess() {
			return this.$resources.plan.data?.monitor_access;
		},

		tabs() {
			let siteConfig = '';
			let siteMonitorTab = '';
			let tabRoute = subRoute => `/sites/${this.siteName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Apps', route: 'apps' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Monitor', route: 'monitor' },
				{ label: 'Database', route: 'database' },
				{ label: 'Config', route: 'site-config' },
				{ label: 'Jobs', route: 'jobs', showRedDot: this.runningJob },
				{ label: 'Logs', route: 'logs' },
				{ label: 'Settings', route: 'settings' }
			];

			if (this.site && this.site?.hide_config !== 1) {
				siteConfig = 'Config';
			}

			if (this.site && this.hasMonitorAccess) {
				siteMonitorTab = 'Monitor';
			}

			let tabsByStatus = {
				Active: [
					'Overview',
					'Apps',
					'Analytics',
					'Database',
					siteConfig,
					'Jobs',
					'Logs',
					'Request Logs',
					'Settings',
					siteMonitorTab
				],
				Inactive: [
					'Overview',
					'Apps',
					'Database',
					siteConfig,
					'Jobs',
					'Logs',
					'Settings'
				],
				Installing: ['Jobs'],
				Pending: ['Jobs'],
				Broken: [
					'Overview',
					'Apps',
					siteConfig,
					'Database',
					'Jobs',
					'Logs',
					'Settings',
					siteMonitorTab
				],
				Suspended: [
					'Overview',
					'Apps',
					'Database',
					'Jobs',
					'Plan',
					'Logs',
					'Settings'
				]
			};
			if (this.site) {
				let tabsToShow = tabsByStatus[this.site?.status];
				if (tabsToShow?.length) {
					tabs = tabs.filter(tab => tabsToShow.includes(tab.label));
				}
				return tabs.map(tab => {
					return {
						...tab,
						route: tabRoute(tab.route)
					};
				});
			}
			return [];
		}
	}
};
</script>
