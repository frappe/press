<template>
	<div>
		<PageHeader title="Apps" subtitle="Manage your marketplace apps">
			<template v-slot:actions>
				<Button
					variant="solid"
					iconLeft="plus"
					@click="
						!$resources.appOptions.data ? $resources.appOptions.fetch() : null;
						showAddAppDialog = true;
					"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<Dialog
			:options="{
				title: 'Add App to Marketplace'
			}"
			v-model="showAddAppDialog"
		>
			<template v-slot:body-content>
				<LoadingText class="py-2" v-if="$resources.appOptions.loading" />
				<AppSourceSelector
					v-else-if="
						$resources.appOptions.data && $resources.appOptions.data.length > 0
					"
					class="mt-1"
					:apps="availableApps"
					v-model="selectedApp"
					:multiple="false"
				/>
				<p v-else class="text-base">No app sources available.</p>

				<ErrorMessage class="mt-2" :message="$resourceErrors" />

				<p class="mt-4 text-base" @click="showAddAppDialog = false">
					Don't find your app here?
					<Link :to="`/marketplace/apps/new`"> Add from GitHub </Link>
				</p>
			</template>
			<template #actions>
				<Button
					variant="solid"
					class="ml-2 w-full"
					v-if="selectedApp"
					:loading="$resources.addMarketplaceApp.loading"
					@click="
						$resources.addMarketplaceApp.submit({
							source: selectedApp.source.name,
							app: selectedApp.app
						})
					"
				>
					Add {{ selectedApp.app }}
				</Button>
			</template>
		</Dialog>

		<Tabs class="pb-32" :tabs="tabs">
			<router-view v-if="$account.team"></router-view>
		</Tabs>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
import AppSourceSelector from '@/components/AppSourceSelector.vue';
import PageHeader from '@/components/global/PageHeader.vue';

export default {
	name: 'Marketplace',
	pageMeta() {
		return {
			title: 'Developer - Frappe Cloud'
		};
	},
	components: {
		Tabs,
		AppSourceSelector,
		PageHeader
	},
	data: () => ({
		tabs: [
			{ label: 'My Apps', route: '/marketplace/apps' },
			{ label: 'Publisher Profile', route: '/marketplace/publisher-profile' },
			{ label: 'Payouts', route: '/marketplace/payouts' }
		],
		showAddAppDialog: false,
		selectedApp: null
	}),
	resources: {
		appOptions() {
			return {
				method: 'press.api.marketplace.options_for_marketplace_app'
			};
		},
		addMarketplaceApp() {
			return {
				method: 'press.api.marketplace.add_app',
				onSuccess() {
					this.showAddAppDialog = false;
					window.location.reload();
				}
			};
		}
	},
	computed: {
		availableApps() {
			return this.$resources.appOptions.data;
		}
	},
	activated() {
		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/apps`);
		}
	},
	beforeRouteUpdate(to, from, next) {
		if (to.path == '/marketplace') {
			next('/marketplace/apps');
		} else {
			next();
		}
	}
};
</script>
