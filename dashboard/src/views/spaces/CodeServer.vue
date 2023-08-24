<template>
	<div>
		<div v-if="codeServer">
			<div class="pb-2">
				<div class="text-base text-gray-700">
					<router-link to="/spaces" class="hover:text-gray-800">
						← Back to Code Servers
					</router-link>
				</div>
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">
							{{ codeServer.name }}
						</h1>
						<Badge
							class="ml-4 hidden md:inline-block"
							:label="codeServer.status"
							:colorMap="$badgeStatusColorMap"
						/>
					</div>
					<div>
						<Button icon-left="external-link" @click="open"> Open </Button>
					</div>
				</div>
			</div>

			<Tabs :tabs="tabs">
				<router-view v-slot="{ Component, route }">
					<component
						v-if="codeServer"
						:is="Component"
						:codeServer="codeServer"
					></component>
				</router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
export default {
	name: 'CodeServer',
	components: {
		Tabs
	},
	props: ['serverName'],
	data() {
		return {
			runningJob: false
		};
	},
	methods: {
		open() {
			window.open(`https://${this.serverName}`, '_blank');
		},
		onSocketUpdate({ doctype, name }) {
			if (doctype === 'Code Server' && name === this.serverName) {
				this.$resources.codeServer.reload();
			}
		},
		setupAgentJobUpdate() {
			if (this._agentJobUpdateSet) return;
			this._agentJobUpdateSet = true;

			this.$socket.on('agent_job_update', data => {
				if (data.name === 'Setup Code Server') {
					if (
						data.status === 'Success' &&
						data.code_server === this.serverName
					) {
						setTimeout(() => {
							// running reload immediately doesn't work for some reason
							this.$router.push(`/codeservers/${this.serverName}/overview`);
							this.$resources.codeServer.reload();
						}, 1000);
					}
				}
				this.runningJob =
					data.code_server === this.serverName && data.status !== 'Success';
			});
		},
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let tab = ['Pending'].includes(this.codeServer.status)
					? 'jobs'
					: 'overview';
				this.$router.replace(`/codeservers/${this.serverName}/${tab}`);
			}
		}
	},
	resources: {
		codeServer() {
			return {
				method: 'press.api.spaces.code_server',
				params: {
					name: this.serverName
				},
				auto: true,
				onError: this.$routeTo404PageIfNotFound
			};
		}
	},
	activated() {
		this.setupAgentJobUpdate();
		if (this.codeServer) {
			this.routeToGeneral();
		} else {
			this.$resources.codeServer.once('onSuccess', () => {
				this.routeToGeneral();
			});
		}

		if (this.codeServer?.status === 'Running') {
			this.$socket.on('list_update', this.onSocketUpdate);
		}
	},
	deactivated() {
		this.$socket.off('list_update', this.onSocketUpdate);
	},
	computed: {
		codeServer() {
			return this.$resources.codeServer.data;
		},
		tabs() {
			let tabRoute = subRoute => `/codeservers/${this.serverName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Jobs', route: 'jobs', showRedDot: this.runningJob }
			];

			let tabsByStatus = {
				Active: ['Overview', 'Jobs'],
				Pending: ['Jobs']
			};
			if (this.codeServer) {
				let tabsToShow = tabsByStatus[this.codeServer.status];
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
