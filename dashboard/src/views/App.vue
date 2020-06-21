<template>
	<div>
		<div class="px-4 sm:px-8" v-if="app">
			<div class="py-8">
				<div class="text-base text-gray-700">
					<router-link to="/apps" class="hover:text-gray-800">
						← Back to Apps
					</router-link>
				</div>
				<div class="flex items-center mt-2">
					<h1 class="text-2xl font-bold">{{ app.name }}</h1>
					<Badge class="ml-4" :status="app.status">{{ app.status }}</Badge>
				</div>
				<a
					:href="app.url"
					target="_blank"
					class="inline-flex items-baseline text-sm text-blue-500 hover:underline"
				>
					Visit Repo
					<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
				</a>
			</div>
			<Alert class="mb-4" v-if="app.status == 'Awaiting Approval'">
				Our engineers are reviewing your code for issues. After review your app
				will be available for installation.
			</Alert>
		</div>
		<div class="px-4 sm:px-8" v-if="app">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view v-bind="{ app }"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs';

export default {
	name: 'App',
	props: ['appName'],
	components: {
		Tabs
	},
	resources: {
		app() {
			return {
				method: 'press.api.app.get',
				params: {
					name: this.appName
				},
				auto: true
			};
		}
	},
	computed: {
		app() {
			return this.$resources.app.data;
		},
		tabs() {
			let tabRoute = subRoute => `/apps/${this.appName}/${subRoute}`;
			let tabs = [
				{ label: 'General', route: 'general' },
				{ label: 'Releases', route: 'releases' },
				{ label: 'Deploys', route: 'deploys' }
			];
			return tabs.map(tab => {
				return {
					...tab,
					route: tabRoute(tab.route)
				};
			});
		}
	},
	activated() {
		this.setupSocketListener();
		this.routeToGeneral();
	},
	methods: {
		setupSocketListener() {
			if (this._socketSetup) return;
			this._socketSetup = true;
			this.$socket.on('list_update', ({ doctype }) => {
				if (doctype === 'App Release') {
					this.$resources.app.reload();
				}
			});
		},
		routeToGeneral() {
			if (this.$route.matched.length === 1) {
				let path = this.$route.fullPath;
				let tab = 'general';
				this.$router.replace(`${path}/${tab}`);
			}
		}
	}
};
</script>
