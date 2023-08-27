<template>
	<div>
		<div v-if="server">
			<div>
				<header
					class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
				>
					<Breadcrumbs
						:items="[
							{ label: 'Security', route: { name: 'Security' } },
							{
								label: server?.title,
								route: {
									name: 'SecurityOverview',
									params: { serverName: server?.name }
								}
							}
						]"
					>
					</Breadcrumbs>
				</header>
				<div
					class="flex flex-col space-y-3 px-5 pt-6 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ server.title }}</h1>
						<Badge class="ml-4" :label="server.status" />
					</div>
				</div>
			</div>
		</div>
		<div class="p-5 pt-1">
			<Tabs :tabs="tabs">
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
	name: 'Security',
	pageMeta() {
		return {
			title: `Security - ${this.serverName} - Frappe Cloud`
		};
	},
	props: ['serverName'],
	components: {
		Tabs
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

		tabs() {
			let tabRoute = subRoute => `/security/${this.serverName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Security Updates', route: 'security_update' },
				{ label: 'Firewall Configuration', route: 'firewall' },
				{ label: 'SSH Session Log', route: 'ssh_session_logs' },
				{ label: 'Nginx Overview', route: 'nginx_overview' }
			];

			let tabsByStatus = {
				Active: [
					'Overview',
					'Security Updates',
					'Firewall Configuration',
					'SSH Session Log',
					'Nginx Overview'
				]
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
