<template>
	<div class="mt-10">
		<div class="px-4 sm:px-8" v-if="app">
			<div class="pb-3">
				<div class="text-base text-gray-700">
					<router-link to="/marketplace/apps" class="hover:text-gray-800">
						← Back to Apps
					</router-link>
				</div>
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ app.title }}</h1>
						<Badge class="ml-4" :status="app.status">{{ app.status }}</Badge>
					</div>
					<div class="space-x-3">
						<Button
							v-if="app.status == 'Published'"
							:link="`/marketplace/apps/${app.name}`"
							icon-left="external-link"
						>
							View in Marketplace
						</Button>
					</div>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="app">
			<Tabs class="pb-8" :tabs="tabs">
				<router-view v-bind="{ app }"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'MarketplaceApp',
	props: ['appName'],
	components: {
		Tabs
	},
	resources: {
		app() {
			return {
				method: 'press.api.marketplace.get_app',
				params: {
					name: this.appName
				},
				auto: true
			};
		}
	},
	activated() {
		if (this.app) {
			this.routeToGeneral();
		} else {
			this.$resources.app.once('onSuccess', () => {
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
		app() {
			if (this.$resources.app.data && !this.$resources.app.loading) {
				return this.$resources.app.data;
			}
			return this.$resources.app.data;
		},
		tabs() {
			let tabRoute = subRoute =>
				`/marketplace/apps/${this.appName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Releases', route: 'releases' },
				{ label: 'Analytics', route: 'analytics' }
			];

			return tabs.map(tab => {
				return {
					...tab,
					route: tabRoute(tab.route)
				};
			});
		}
	}
};
</script>
