<template>
	<div class="space-y-12">
		<div v-if="publicApps.length">
			<h2 class="text-sm font-medium leading-6 text-gray-900">
				Select Marketplace Apps
			</h2>
			<div class="mt-2 w-full space-y-2">
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-2">
					<button
						v-for="app in publicApps"
						:key="app"
						@click="toggleApp(app)"
						:class="[
							apps.map(a => a.app).includes(app.app)
								? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
								: 'bg-white text-gray-900  hover:bg-gray-50',
							'flex w-full items-start space-x-2 rounded border p-2 text-left text-base text-gray-900'
						]"
					>
						<img :src="app.image" class="h-10 w-10 shrink-0" />
						<div class="w-full">
							<div class="flex w-full items-center justify-between">
								<div class="flex items-center space-x-2">
									<div class="text-base font-medium">
										{{ app.app_title }}
									</div>
									<Tooltip
										v-if="app.total_installs > 1"
										:text="`${app.total_installs} installs`"
									>
										<div class="flex items-center text-sm text-gray-600">
											<i-lucide-download class="h-3 w-3" />
											<span class="ml-0.5 leading-3">
												{{ $format.numberK(app.total_installs || '') }}
											</span>
										</div>
									</Tooltip>
									<Badge
										theme="gray"
										:label="
											app.subscription_type === 'Freemium'
												? 'Paid'
												: app.subscription_type
										"
									/>
								</div>
								<a :href="`/${app.route}`" target="_blank" title="App details">
									<FeatherIcon name="external-link" class="h-4 w-4" />
								</a>
							</div>
							<div
								class="mt-1 line-clamp-1 overflow-clip text-p-sm text-gray-600"
								:title="app.description"
							>
								{{ app.description }}
							</div>
						</div>
					</button>
				</div>
			</div>
			<SiteAppPlanSelectorDialog
				v-if="selectedApp"
				v-model="showAppPlanSelectorDialog"
				:app="selectedApp"
				@plan-select="
					plan => {
						apps.push({ app: selectedApp.app, plan });
						showAppPlanSelectorDialog = false;
					}
				"
			/>
		</div>
		<div v-if="!siteOnPublicBench && privateApps.length">
			<h2 class="text-sm font-medium leading-6 text-gray-900">
				Select Private Apps
			</h2>
			<div class="mt-2 w-full space-y-2">
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-2">
					<button
						v-for="app in privateApps"
						:key="app"
						@click="toggleApp(app)"
						:class="[
							apps.map(a => a.app).includes(app.app)
								? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
								: 'bg-white text-gray-900  hover:bg-gray-50',
							'flex h-12 w-full items-center space-x-2 rounded border p-2 text-left text-base text-gray-900'
						]"
					>
						<div class="text-base font-medium">
							{{ app.app_title }}
						</div>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import SiteAppPlanSelectorDialog from './SiteAppPlanSelectorDialog.vue';

export default {
	props: ['availableApps', 'siteOnPublicBench', 'modelValue'],
	emits: ['update:modelValue'],
	components: {
		SiteAppPlanSelectorDialog
	},
	data() {
		return {
			selectedApp: null,
			showAppPlanSelectorDialog: false,
			apps: []
		};
	},
	computed: {
		publicApps() {
			return (this.availableApps || []).filter(
				app => (app.public || app.plans?.length) && app.image
			);
		},
		privateApps() {
			return (this.availableApps || []).filter(
				app => !this.publicApps.includes(app)
			);
		}
	},
	methods: {
		toggleApp(app) {
			if (this.apps.map(a => a.app).includes(app.app)) {
				this.apps = this.apps.filter(a => a.app !== app.app);
			} else {
				if (app.plans?.length) {
					this.selectedApp = app;
					this.showAppPlanSelectorDialog = true;
				} else {
					this.apps.push({ app: app.app });
				}
			}
			this.$emit('update:modelValue', this.apps);
		}
	}
};
</script>
