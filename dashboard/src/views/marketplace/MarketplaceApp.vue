<template>
	<div v-if="app">
		<div>
			<header
				class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
			>
				<Breadcrumbs
					:items="[
						{
							label: 'Apps',
							route: {
								name: 'Marketplace',
								params: { appName: app.name }
							}
						},
						{
							label: app.title,
							route: {
								name: 'MarketplaceAppOverview',
								params: { appName: app.name }
							}
						}
					]"
				>
					<template v-slot:actions>
						<Button
							v-if="app.status === 'Published'"
							variant="solid"
							icon-left="external-link"
							label="View in Marketplace"
							class="ml-2"
							:link="`/marketplace/apps/${app.name}`"
						/>
					</template>
				</Breadcrumbs>
			</header>
		</div>
		<div>
			<div class="px-5 pt-5">
				<div
					class="flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mb-3 flex items-center">
						<h1 class="text-2xl font-bold">{{ app.title }}</h1>
						<Badge class="ml-4" :label="app.status" />
					</div>
				</div>
			</div>
			<div class="p-5 pt-1">
				<Tabs :tabs="tabs">
					<router-view v-bind="{ app }"></router-view>
				</Tabs>
			</div>
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
				url: 'press.api.marketplace.get_app',
				params: {
					name: this.appName
				},
				auto: true,
				onError: this.$routeTo404PageIfNotFound,
				onSuccess() {
					this.routeToGeneral();
				}
			};
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
			let tabsByStatus = {
				Draft: ['Overview', 'Releases', 'Review'],
				'In Review': ['Overview', 'Releases', 'Review'],
				Rejected: ['Overview', 'Releases', 'Review'],
				Published: [
					'Overview',
					'Releases',
					'Analytics',
					'Subscriptions',
					'Pricing'
				],
				'Attention Required': [
					'Overview',
					'Releases',
					'Review',
					'Analytics',
					'Subscriptions',
					'Pricing'
				]
			};
			let tabRoute = subRoute =>
				`/marketplace/apps/${this.appName}/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Releases', route: 'releases' },
				{ label: 'Review', route: 'review' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Subscriptions', route: 'subscriptions' },
				{ label: 'Pricing', route: 'pricing' }
			];

			if (this.app) {
				let tabsToShow = tabsByStatus[this.app.status];

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
