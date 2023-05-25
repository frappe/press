<template>
	<div>
		<div v-if="server">
			<div class="pb-3">
				<div class="text-base text-gray-700">
					<router-link to="/servers" class="hover:text-gray-800">
						← Back to Servers
					</router-link>
				</div>
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ server.title }}</h1>
						<Badge
							class="ml-4 hidden md:inline-block"
							:label="server.status"
							:colorMap="$badgeStatusColorMap"
						></Badge>

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
							<Badge :label="server.status" :colorMap="$badgeStatusColorMap" />
							<div
								v-if="regionInfo"
								class="ml-2 flex cursor-default flex-row items-center rounded-md bg-yellow-50 px-3 py-1 text-xs font-medium text-yellow-700"
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

						<!-- Only for mobile view -->
						<Dropdown
							v-if="serverActions.length > 0"
							:options="serverActions"
							right
						>
							<template v-slot="{ open }">
								<Button icon-right="chevron-down">Actions</Button>
							</template>
						</Dropdown>
					</div>

					<div class="hidden flex-row space-x-3 md:flex">
						<Button
							v-for="action in serverActions"
							v-if="serverActions.length <= 2"
							:key="action.label"
							:icon-left="action.icon"
							:loading="action.loading"
							:route="action.route"
							@click="action.action"
						>
							{{ action.label }}
						</Button>

						<Dropdown v-if="serverActions.length > 2" :options="serverActions">
							<template v-slot="{ open }">
								<Button icon-right="chevron-down">Actions</Button>
							</template>
						</Dropdown>
					</div>
				</div>
			</div>
		</div>
		<div>
			<Tabs class="pb-8" :tabs="tabs">
				<router-view v-slot="{ Component, route }">
					<component v-if="server" :is="Component" :server="server"></component>
				</router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'Server',
	pageMeta() {
		return {
			title: `Server - ${this.serverName} - Frappe Cloud`
		};
	},
	props: ['serverName'],
	components: {
		Tabs
	},
	data() {
		return {
			runningJob: false,
			runningPlay: false,
			errorMessage: ''
		};
	},
	resources: {
		server() {
			return {
				method: 'press.api.server.get',
				params: {
					name: this.serverName
				},
				auto: true,
				onSuccess() {},
				onError: this.$routeTo404PageIfNotFound
			};
		},
		reboot() {
			return {
				method: 'press.api.server.reboot',
				params: {
					name: this.serverName
				},
				onSuccess(data) {
					this.$notify({
						title: 'Server Reboot Scheduled Successfully',
						color: 'green',
						icon: 'check'
					});
					this.$resources.server.reload();
				},
				onError() {
					this.$notify({
						title: 'An error occurred',
						color: 'red',
						icon: 'x'
					});
				}
			};
		}
	},
	activated() {
		if (this.server) {
			this.routeToGeneral();
		} else {
			this.$resources.server.once('onSuccess', () => {
				this.routeToGeneral();
			});
		}
	},
	methods: {
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let path = this.$route.fullPath;
				this.$router.replace(`${path}/overview`);
			}
		}
	},
	computed: {
		server() {
			return this.$resources.server.data;
		},

		regionInfo() {
			if (!this.$resources.server.loading && this.$resources.server.data) {
				return this.$resources.server.data.region_info;
			}
			return null;
		},

		serverActions() {
			return [
				['Active', 'Updating'].includes(this.server.status) && {
					label: 'Visit Server',
					icon: 'external-link',
					handler: () => {
						window.open(`https://${this.server.name}`, '_blank');
					}
				},
				this.server.status === 'Active' && {
					label: 'New Bench',
					icon: 'plus',
					handler: () => {
						this.$router.replace(
							`/servers/${this.server.app_server}/bench/new`
						);
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'View in Desk',
					icon: 'external-link',
					handler: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/server/${this.server.name}`,
							'_blank'
						);
					}
				},
				this.server.status === 'Active' && {
					label: 'Reboot',
					icon: 'tool',
					loading: this.$resources.reboot.loading,
					handler: () => {
						return this.$resources.reboot.submit();
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'Impersonate Team',
					icon: 'tool',
					handler: async () => {
						await this.$account.switchTeam(this.server.team);
						this.$notify({
							title: 'Switched Team',
							message: `Switched to ${this.server.team}`,
							icon: 'check',
							color: 'green'
						});
					}
				}
			].filter(Boolean);
		},

		tabs() {
			let tabRoute = subRoute => `/servers/${this.serverName}/${subRoute}`;
			let tabs = [
				{ label: 'Installing', route: 'install' },
				{ label: 'Overview', route: 'overview' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Benches', route: 'benches' },
				{ label: 'Jobs', route: 'jobs', showRedDot: this.runningJob },
				{ label: 'Plays', route: 'plays', showRedDot: this.runningPlay }
			];

			let tabsByStatus = {
				Active: ['Overview', 'Analytics', 'Benches', 'Jobs', 'Plays'],
				Pending: ['Installing'],
				Installing: ['Installing',"Plays"]
			};
			if (this.server) {
				let tabsToShow = tabsByStatus[this.server.status];
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
