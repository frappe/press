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
						<h1 class="text-2xl font-bold">{{ server.name }}</h1>
						<Badge
							class="ml-4 hidden md:inline-block"
							:status="server.status"
							:colorMap="$badgeStatusColorMap"
							>{{ server.status }}</Badge
						>

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
							<Badge :status="server.status" :colorMap="$badgeStatusColorMap">{{
								server.status
							}}</Badge>
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
							:items="serverActions"
							right
						>
							<template v-slot="{ toggleDropdown }">
								<Button icon-right="chevron-down" @click="toggleDropdown()"
									>Actions</Button
								>
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

						<Dropdown v-if="serverActions.length > 2" :items="serverActions">
							<template v-slot="{ toggleDropdown }">
								<Button icon-right="chevron-down" @click="toggleDropdown()"
									>Actions</Button
								>
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
				onError(e) {
					if (e.indexOf('not found') >= 0) {
						this.$router.replace('/404NotFound');
					}
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
					action: () => {
						window.open(`https://${this.server.name}`, '_blank');
					}
				},
				this.$account.user.user_type == 'System User' && {
					label: 'View in Desk',
					icon: 'external-link',
					action: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/server/${this.server.name}`,
							'_blank'
						);
					}
				}
			].filter(Boolean);
		},

		tabs() {
			let tabRoute = subRoute => `/servers/${this.serverName}/${subRoute}`;
			let tabs = [{ label: 'Overview', route: 'overview' }];

			let tabsByStatus = {
				Active: ['Overview']
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
