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
					<div></div>
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
	resources: {
		codeServer() {
			return {
				method: 'press.api.spaces.code_server',
				params: {
					name: this.serverName
				},
				auto: true
			};
		}
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
