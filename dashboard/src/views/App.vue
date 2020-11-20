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
					<h1 class="text-2xl font-bold">{{ app.title }}</h1>
				</div>
			</div>
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
				{ label: 'Sources', route: 'sources' },
				{ label: 'Releases', route: 'releases' }
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
				if (doctype === 'Application Release') {
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
