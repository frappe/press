<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs
				:items="[
					{ label: 'Sites', route: { name: 'Sites' } },
					{
						label: site?.host_name || site?.name,
						route: { name: 'SiteOverview', params: { siteName: site?.name } }
					}
				]"
			>
				<template #actions>
					<div>
						<Dropdown :options="siteActions">
							<template v-slot="{ open }">
								<Button variant="ghost" class="mr-2" icon="more-horizontal" />
							</template>
						</Dropdown>
						<Button
							v-if="site?.status === 'Active'"
							variant="solid"
							icon-left="external-link"
							label="Visit Site"
							@click="$router.push(`/${this.site?.name}/new`)"
						/>
					</div>
				</template>
			</BreadCrumbs>
		</header>
		<div v-if="site">
			<div class="px-5 pt-6">
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
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
			</div>
		</div>
		<div class="p-5 pt-1">
			<Tabs :tabs="tabs">
				<router-view v-slot="{ Component, route }">
					<component v-if="site" :is="Component" :site="site"></component>
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
				<Input
					label="Reason for logging in as Administrator"
					type="textarea"
					v-model="reasonForAdminLogin"
					required
				/>
				<ErrorMessage class="mt-3" :message="errorMessage" />
			</template>
		</Dialog>

		<Dialog
			:options="{
				title: 'Transfer Site to Team',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						onClick: () =>
							$resources.transferSite.submit({
								team: emailOfChildTeam,
								name: siteName
							})
					}
				]
			}"
			v-model="showTransferSiteDialog"
		>
			<template #body-content>
				<Input
					label="Enter title of the child team"
					type="text"
					v-model="emailOfChildTeam"
					required
				/>

				<ErrorMessage class="mt-3" :message="$resources.transferSite.error" />
			</template>
		</Dialog>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
import { loginAsAdmin } from '@/controllers/loginAsAdmin';

export default {
	name: 'Site',
	pageMeta() {
		return {
			title: `Site - ${this.siteName} - Frappe Cloud`
		};
	},
	props: ['siteName'],
	components: {
		Tabs
	},
	data() {
		return {
			runningJob: false,
			reasonForAdminLogin: '',
			showReasonForAdminLoginDialog: false,
			showTransferSiteDialog: false,
			emailOfChildTeam: null,
			errorMessage: ''
		};
	},
	resources: {
		site() {
			return {
				method: 'press.api.site.get',
				params: {
					name: this.siteName
				},
				auto: true,
				onSuccess() {
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
		transferSite() {
			return {
				method: 'press.api.site.change_team',
				onSuccess() {
					this.showTransferSiteDialog = false;
					this.emailOfChildTeam = null;
					this.$notify({
						title: 'Site Transferred to Child Team',
						message: 'Site Transferred to Child Team',
						color: 'green',
						icon: 'check'
					});
				}
			};
		}
	},
	activated() {
		this.setupAgentJobUpdate();
		if (this.site) {
			this.routeToGeneral();
		} else {
			this.$resources.site.once('onSuccess', () => {
				this.routeToGeneral();
			});
		}

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
				['Active', 'Updating'].includes(this.site?.status) && {
					label: 'Visit Site',
					icon: 'external-link',
					onClick: () => {
						window.open(`https://${this.site?.name}`, '_blank');
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'View in Desk',
					icon: 'external-link',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/site/${this.site?.name}`,
							'_blank'
						);
					}
				},
				this.site?.group && {
					label: 'Manage Bench',
					icon: 'tool',
					route: `/benches/${this.site?.group}`,
					onClick: () => {
						this.$router.push(`/benches/${this.site?.group}`);
					}
				},
				this.site?.status == 'Active' && {
					label: 'Login As Administrator',
					icon: 'external-link',
					loading: this.$resources.loginAsAdmin.loading,
					onClick: () => {
						if (this.$account.team.name == this.site?.notify_email) {
							return this.$resources.loginAsAdmin.submit({
								name: this.siteName
							});
						}

						this.showReasonForAdminLoginDialog = true;
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'Impersonate Team',
					icon: 'tool',
					onClick: async () => {
						await this.$account.switchTeam(this.site?.team);
						this.$notify({
							title: 'Switched Team',
							message: `Switched to ${this.site?.team}`,
							icon: 'check',
							color: 'green'
						});
					}
				},
				this.site?.status == 'Active' && {
					label: 'Transfer Site',
					icon: 'tool',
					loading: this.$resources.transferSite.loading,
					onClick: () => {
						this.showTransferSiteDialog = true;
					},
					condition: () => {
						return !this.$account.parent_team;
					}
				}
			].filter(Boolean);
		},

		tabs() {
			let siteConfig = '';
			let tabRoute = subRoute => `/sites/${this.siteName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Apps', route: 'apps' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Database', route: 'database' },
				{ label: 'Site Config', route: 'site-config' },
				{ label: 'Jobs', route: 'jobs', showRedDot: this.runningJob },
				{ label: 'Logs', route: 'logs' },
				{ label: 'Settings', route: 'setting' }
			];

			if (this.site && this.site?.hide_config !== 1) {
				siteConfig = 'Site Config';
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
					'Settings'
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
					'Settings'
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
