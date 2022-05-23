<template>
	<div class="mt-8 flex-1">
		<div class="flex items-center justify-between pb-4">
			<h3 class="text-xl font-bold">Apps</h3>
			<Button
				type="primary"
				iconLeft="plus"
				@click="
					!$resources.appOptions.data ? $resources.appOptions.fetch() : null;
					showAddAppDialog = true;
				"
			>
				Add App
			</Button>
		</div>
		<div
			class="py-2 px-2 sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
		>
			<div
				class="py-2 text-base text-gray-600 sm:px-2"
				v-if="apps.length === 0"
			>
				No apps.
			</div>

			<div class="py-2" v-for="app in apps" :key="app.name">
				<router-link
					:to="`/saas/manage/${app.name}/overview`"
					class="block rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between sm:justify-start">
						<div class="text-base sm:w-4/12">
							{{ app.title }}
						</div>
						<div class="text-base sm:w-4/12">
							<Badge class="pointer-events-none" v-bind="appBadge(app)" />
						</div>
						<div class="text-right text-base sm:w-4/12">
							{{ app.count }} sites
						</div>
					</div>
				</router-link>
			</div>
		</div>

		<Dialog
			title="Add App to Marketplace"
			:dismissable="true"
			v-model="showAddAppDialog"
		>
			<Loading class="py-2" v-if="$resources.appOptions.loading" />
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
			<template #actions>
				<Button
					type="primary"
					class="ml-2"
					v-if="selectedApp"
					:loading="$resources.addSaasApp.loading"
					@click="
						$resources.addSaasApp.submit({
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
				<Link :to="`/saas/manage/new`"> Add from GitHub </Link>
			</p>
		</Dialog>
	</div>
</template>

<script>
import AppSourceSelector from '@/components/AppSourceSelector.vue';

export default {
	name: 'SaasManage',
	components: {
		AppSourceSelector
	},
	data: () => ({
		apps: [],
		showAddAppDialog: false,
		selectedApp: null
	}),
	methods: {
		appBadge(app) {
			let status = app.status;
			let color = app.status == 'Draft' ? 'yellow' : 'green';

			return {
				color,
				status
			};
		}
	},
	resources: {
		apps: {
			method: 'press.api.saas.get_apps',
			auto: true,
			onSuccess(r) {
				this.apps = r;
			}
		},
		appOptions() {
			return {
				method: 'press.api.saas.options_for_saas_app'
			};
		},
		addSaasApp() {
			return {
				method: 'press.api.saas.add_app',
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
	}
};
</script>
