<template>
	<div class="mt-8">
		<div class="px-4 sm:px-8">
			<div class="pb-3">
				<div class="flex items-center justify-between">
					<h1 class="text-3xl font-bold">Manage Apps</h1>
					<Button
						type="primary"
						iconLeft="plus"
						@click="
							!appOptions.data ? appOptions.fetch() : null;
							showAddAppDialog = true;
						"
					>
						Add App
					</Button>
				</div>
			</div>
		</div>

		<Dialog
			title="Add App to Marketplace"
			:dismissable="true"
			v-model="showAddAppDialog"
		>
			<Loading class="py-2" v-if="appOptions.loading" />
			<AppSourceSelector
				v-else-if="appOptions.data && appOptions.data.length > 0"
				class="mt-1"
				:apps="availableApps"
				:value.sync="selectedApp"
				:multiple="false"
			/>
			<p v-else class="text-base">No app sources available.</p>
			<template #actions>
				<Button
					type="primary"
					class="ml-2"
					v-if="selectedApp"
					:loading="addMarketplaceApp.loading"
					@click="
						addMarketplaceApp.submit({
							source: selectedApp.source.name,
							app: selectedApp.app
						})
					"
				>
					Add {{ selectedApp.app }}
				</Button>
			</template>

			<ErrorMessage class="mt-2" :error="$resourceErrors" />

			<p class="mt-4 text-base" @click="showAddAppDialog = false">
				Don't find your app here?
				<Link :to="`/marketplace/apps/new`">
					Add from GitHub
				</Link>
			</p>
		</Dialog>

		<div class="px-4 sm:px-8">
			<Tabs class="pb-32" :tabs="tabs">
				<router-view v-if="$account.team"></router-view>
			</Tabs>
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';
import AppSourceSelector from '@/components/AppSourceSelector.vue';

export default {
	name: 'Marketplace',
	components: {
		Tabs,
		AppSourceSelector
	},
	data: () => ({
		tabs: [
			{ label: 'My Apps', route: '/marketplace/apps' },
			{ label: 'Publisher Profile', route: '/marketplace/publisher-profile' }
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
			return this.appOptions.data;
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
