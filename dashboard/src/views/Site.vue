<template>
	<div>
		<div class="px-4 sm:px-8" v-if="site">
			<div class="py-8">
				<div class="text-base text-gray-700">
					<router-link to="/sites" class="hover:text-gray-800">
						← Back to Sites
					</router-link>
				</div>
				<div class="flex items-center mt-2">
					<h1 class="text-2xl font-bold">{{ site.name }}</h1>
					<Badge class="ml-4" :status="site.status">{{ site.status }}</Badge>
				</div>
				<a
					v-if="site.status === 'Active' || site.status === 'Updating'"
					:href="`https://${site.name}`"
					target="_blank"
					class="inline-flex items-baseline text-sm text-blue-500 hover:underline"
				>
					Visit Site
					<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
				</a>
			</div>
			<Alert
				class="mb-4"
				v-if="site.status == 'Active' && !site.setup_wizard_complete"
			>
				Please
				<a
					@click="loginAsAdministrator(siteName)"
					class="border-b border-orange-700 cursor-pointer"
				>
					login
				</a>
				and complete the setup wizard on your site. Analytics will be collected
				only after setup is complete.
			</Alert>
		</div>
		<div class="px-4 sm:px-8" v-if="site">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view v-bind="{ site }"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs';

export default {
	name: 'Site',
	props: ['siteName'],
	components: {
		Tabs
	},
	resources: {
		site() {
			return {
				method: 'press.api.site.get',
				params: {
					name: this.siteName
				},
				auto: true,
				onSuccess: async () => {
					if (
						this.site.status === 'Active' &&
						!this.site.setup_wizard_complete
					) {
						this.site.setup_wizard_complete = Boolean(
							await this.$call('press.api.site.setup_wizard_complete', {
								name: this.siteName
							})
						);
					}
				}
			};
		}
	},
	provide() {
		return {
			utils: {
				loginAsAdministrator: this.loginAsAdministrator
			}
		};
	},
	activated() {
		this.setupSocket();
		if (this.site) {
			this.routeToGeneral();
		} else {
			this.$resources.site.once('onSuccess', () => {
				this.routeToGeneral();
			});
		}
	},
	methods: {
		async loginAsAdministrator(siteName) {
			let sid = await this.$call('press.api.site.login', {
				name: siteName
			});
			if (sid) {
				window.open(`https://${siteName}/desk?sid=${sid}`, '_blank');
			}
		},
		setupSocket() {
			if (this._socketSetup) return;
			this._socketSetup = true;
			this.$socket.on('agent_job_update', data => {
				if (data.name === 'New Site' || data.name === 'New Site from Backup') {
					if (data.status === 'Success' && data.site === this.siteName) {
						this.$resources.site.reload();
					}
				}
			});
			this.$socket.on('list_update', ({ doctype, name }) => {
				if (doctype === 'Site' && name === this.siteName) {
					this.$resources.site.reload();
				}
			});
		},
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let path = this.$route.fullPath;
				let tab = 'general';
				if (['Pending', 'Installing'].includes(this.site.status)) {
					tab = 'installing';
				}
				this.$router.replace(`${path}/${tab}`);
			}
		}
	},
	computed: {
		site() {
			return this.$resources.site.data;
		},
		tabs() {
			let tabRoute = subRoute => `/sites/${this.siteName}/${subRoute}`;
			let tabs = [
				{ label: 'General', route: 'general' },
				{ label: 'Installing', route: 'installing' },
				{ label: 'Plan', route: 'plan' },
				{ label: 'Apps', route: 'apps' },
				{ label: 'Domains', route: 'domains' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Backups', route: 'backups' },
				{ label: 'Database', route: 'database' },
				{ label: 'Site Config', route: 'site-config' },
				{ label: 'Activity', route: 'activity' },
				{ label: 'Jobs', route: 'jobs' },
				{ label: 'Request Logs', route: 'request-logs' }
			];

			let tabsByStatus = {
				Active: [
					'General',
					'Plan',
					'Apps',
					'Domains',
					'Analytics',
					'Backups',
					'Database',
					'Site Config',
					'Activity',
					'Jobs',
					'Request Logs'
				],
				Inactive: ['General', 'Plan', 'Site Config', 'Activity', 'Jobs'],
				Installing: ['Installing', 'Jobs'],
				Pending: ['Installing', 'Jobs'],
				Broken: ['General', 'Plan', 'Activity', 'Jobs'],
				Suspended: ['General', 'Activity', 'Jobs']
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
