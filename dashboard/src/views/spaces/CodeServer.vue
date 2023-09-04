<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs
				:items="[
					{ label: 'Spaces', route: { name: 'Spaces' } },
					{
						label: serverName,
						route: {
							name: 'CodeServerOverview',
							params: { serverName: serverName }
						}
					}
				]"
			>
				<template #actions>
					<div>
						<Dropdown :options="codeServerActions">
							<template v-slot="{ open }">
								<Button variant="ghost" class="mr-2" icon="more-horizontal" />
							</template>
						</Dropdown>
					</div>
				</template>
			</Breadcrumbs>
		</header>

		<div v-if="codeServer" class="p-5">
			<div class="pb-2">
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">
							{{ codeServer.name }}
						</h1>
						<Badge
							class="ml-4"
							:label="codeServer.status"
							:colorMap="$badgeStatusColorMap"
						/>
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
				url: 'press.api.spaces.code_server',
				params: {
					name: this.serverName
				},
				auto: true,
				onSuccess: this.routeToGeneral,
				onError: this.$routeTo404PageIfNotFound
			};
		}
	},
	activated() {
		this.setupAgentJobUpdate();

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
		},
		codeServerActions() {
			return [
				{
					label: 'Open',
					icon: 'external-link',
					onClick: () => {
						window.open(`https://${this.serverName}`, '_blank');
					}
				}
			];
		}
	}
};
</script>
