<template>
	<div class="mt-10">
		<div class="px-4 sm:px-8" v-if="site">
			<div class="pb-3">
				<div class="text-base text-gray-700">
					<router-link to="/sites" class="hover:text-gray-800">
						← Back to Sites
					</router-link>
				</div>
				<div
					class="flex flex-col space-y-3 md:space-y-0 md:justify-between md:flex-row md:items-baseline"
				>
					<div class="flex items-center mt-2">
						<h1 class="text-2xl font-bold">{{ site.name }}</h1>
						<Badge class="hidden md:inline-block ml-4" :status="site.status">{{
							site.status
						}}</Badge>

						<div
							v-if="regionInfo"
							class="hidden ml-2 self-end md:flex flex-row items-center px-3 py-1 text-xs font-medium rounded-md cursor-default text-yellow-700 bg-yellow-50"
						>
							<img
								v-if="regionInfo.image"
								class="h-4 mr-2"
								:src="regionInfo.image"
								:alt="`Flag of ${regionInfo.title}`"
								:title="regionInfo.image"
							/>
							<p>{{ regionInfo.title }}</p>
						</div>
					</div>
					<div class="mb-10 md:hidden flex flex-row justify-between">
						<div class="flex flex-row">
							<Badge :status="site.status">{{ site.status }}</Badge>
							<div
								v-if="regionInfo"
								class="ml-2 flex flex-row items-center px-3 py-1 text-xs font-medium rounded-md cursor-default text-yellow-700 bg-yellow-50"
							>
								<img
									v-if="regionInfo.image"
									class="h-4 mr-2"
									:src="regionInfo.image"
									:alt="`Flag of ${regionInfo.title}`"
									:title="regionInfo.image"
								/>
								<p>{{ regionInfo.title }}</p>
							</div>
						</div>

						<!-- Only for mobile view -->
						<Dropdown :items="siteActions" right>
							<template v-slot="{ toggleDropdown }">
								<Button icon-right="chevron-down" @click="toggleDropdown()"
									>Actions</Button
								>
							</template>
						</Dropdown>
					</div>

					<div class="hidden md:flex flex-row space-x-3">
						<Button
							v-for="action in siteActions"
							:key="action.label"
							:icon-left="action.icon"
							:loading="action.loading"
							@click="action.action"
						>
							{{ action.label }}
						</Button>
					</div>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="site">
			<Tabs class="pb-8" :tabs="tabs">
				<router-view v-bind="{ site }"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
import { loginAsAdmin } from '@/controllers/loginAsAdmin';

export default {
	name: 'Site',
	props: ['siteName'],
	components: {
		Tabs
	},
	data() {
		return {
			runningJob: false
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
					if (this.site.status !== 'Active' || this.site.setup_wizard_complete)
						return;

					this.$call('press.api.site.setup_wizard_complete', {
						name: this.siteName
					})
						.then(complete => {
							this.site.setup_wizard_complete = Boolean(complete);
						})
						.catch(() => (this.site.setup_wizard_complete = false));
				}
			};
		},
		loginAsAdmin() {
			return loginAsAdmin(this.siteName);
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
				let path = this.$route.fullPath;
				let tab = ['Pending', 'Installing'].includes(this.site.status)
					? 'jobs'
					: 'overview';
				this.$router.replace(`${path}/${tab}`);
			}
		},
		reasonToLoginAsAdminPopup() {
			if (this.$account.team.name == this.site.team) {
				return this.$resources.loginAsAdmin.submit({
					name: this.siteName
				});
			}
			this.$confirm({
				title: 'Login as Administrator',
				message: 'Please enter reason for this login.',
				actionLabel: 'Login',
				textBox: true,
				action: (closeDialog, textBoxInput) => {
					let reason = textBoxInput;
					if (textBoxInput.trim()) {
						this.$resources.loginAsAdmin.submit({
							name: this.siteName,
							reason: reason
						});
						closeDialog();
					} else {
						this.$notify({
							title: 'Reason field should not be empty',
							color: 'red',
							icon: 'x'
						});
					}
				}
			});
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
				this.site.group && {
					label: 'Manage Bench',
					icon: 'tool',
					action: () => this.$router.push(`/benches/${this.site.group}`)
				},
				this.site.status == 'Active' && {
					label: 'Login As Administrator',
					icon: 'external-link',
					loading: this.$resources.loginAsAdmin.loading,
					action: this.reasonToLoginAsAdminPopup // TODO: refactor, variable name doesn't make sense and also implementation could be much better
				},
				['Active', 'Updating'].includes(this.site.status) && {
					label: 'Visit Site',
					icon: 'external-link',
					action: () => {
						window.open(`https://${this.site.name}`, '_blank');
					}
				}
			].filter(Boolean);
		},

		tabs() {
			let tabRoute = subRoute => `/sites/${this.siteName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Backup & Restore', route: 'database' },
				{ label: 'Site Config', route: 'site-config' },
				{ label: 'Jobs', route: 'jobs', showRedDot: this.runningJob },
				{ label: 'Logs', route: 'logs' },
				{ label: 'Activity', route: 'activity' }
			];

			let tabsByStatus = {
				Active: [
					'Overview',
					'Analytics',
					'Backup & Restore',
					'Site Config',
					'Activity',
					'Jobs',
					'Logs',
					'Request Logs'
				],
				Inactive: [
					'Overview',
					'Backup & Restore',
					'Site Config',
					'Activity',
					'Jobs',
					'Logs'
				],
				Installing: ['Jobs'],
				Pending: ['Jobs'],
				Broken: [
					'Overview',
					'Site Config',
					'Backup & Restore',
					'Activity',
					'Jobs',
					'Logs'
				],
				Suspended: ['Overview', 'Activity', 'Backup & Restore', 'Jobs', 'Plan']
			};
			if (this.site) {
				let tabsToShow = tabsByStatus[this.site.status];
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
