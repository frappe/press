<template>
	<div>
		<div class="px-4 sm:px-8" v-if="site">
			<div class="py-8">
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
						<Badge class="ml-4" :status="site.status">{{ site.status }}</Badge>
					</div>
					<div class="space-x-3">
						<Button
							v-if="site.status == 'Active'"
							@click="loginAsAdministrator(siteName)"
							icon-left="external-link"
						>
							Login as Administrator
						</Button>
						<Button
							v-if="site.status === 'Active' || site.status === 'Updating'"
							:link="`https://${site.name}`"
							icon-left="external-link"
						>
							Visit Site
						</Button>
					</div>
				</div>
			</div>
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
		}
	},
	provide() {
		return {
			loginAsAdministrator: this.loginAsAdministrator
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
						// running reload immediately doesn't work for some reason
						setTimeout(() => this.$resources.site.reload(), 1000);
					}
				}
				this.runningJob =
					data.site === this.siteName && data.status !== 'Success';
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
				let tab = 'overview';
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
				{ label: 'Overview', route: 'overview' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Backup & Restore', route: 'database' },
				{ label: 'Site Config', route: 'site-config' },
				{ label: 'Activity', route: 'activity' },
				{ label: 'Jobs', route: 'jobs', showRedDot: this.runningJob },
				{ label: 'Site Logs', route: 'logs' },
				{ label: 'Request Logs', route: 'request-logs' }
			];

			let tabsByStatus = {
				Active: [
					'Overview',
					'Analytics',
					'Backup & Restore',
					'Site Config',
					'Activity',
					'Jobs',
					'Site Logs',
					'Request Logs'
				],
				Inactive: [
					'Overview',
					'Backup & Restore',
					'Site Config',
					'Activity',
					'Jobs',
					'Site Logs'
				],
				Pending: ['Overview', 'Jobs', 'Site Logs'],
				Broken: [
					'Overview',
					'Site Config',
					'Backup & Restore',
					'Activity',
					'Jobs',
					'Site Logs'
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
