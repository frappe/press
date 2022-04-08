<template>
	<div class="px-4 py-4 text-base sm:px-8">
		<Button v-if="$resources.opionsForQuickInstall" :loading="true"
			>Loading</Button
		>
		<div v-else>
			<h1 class="mb-4 text-xl font-semibold">
				Install App: {{ options ? options.title : '' }}
			</h1>

			<ErrorMessage :error="$resources.optionsForQuickInstall.error" />

			<div v-if="options" class="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
				<Card title="Sites" subtitle="Select a site to install">
					<ul v-if="options.sites?.length">
						<li
							v-for="site in options.sites"
							class="flex w-full flex-row justify-between rounded-md py-2 px-1 text-left text-base hover:bg-gray-50"
						>
							<p>
								{{ site }}
							</p>
							<Button
								@click="installAppOnSite(site)"
								:loading="
									$resources.installAppOnSite.loading &&
									$resources.installAppOnSite.currentParams.name === site
								"
								>Install</Button
							>
						</li>
					</ul>

					<div v-else>
						<p class="text-sm text-gray-700">No site available for install</p>
					</div>

					<template v-slot:actions>
						<Button type="primary" route="/sites/new">New Site</Button>
					</template>
				</Card>

				<Card title="Private Benches" subtitle="Select a bench to install">
					<ul v-if="options.release_groups?.length" class="space-y-3">
						<li
							v-for="bench in options.release_groups"
							class="flex w-full flex-row justify-between rounded-md py-2 px-1 text-left text-base hover:bg-gray-50"
						>
							<p>
								{{ bench.title }}
							</p>
							<Button
								@click="addAppToBench(bench)"
								:loading="
									$resources.addAppToBench.loading &&
									$resources.addAppToBench.currentParams.name === bench.name
								"
								>Add</Button
							>
						</li>
					</ul>

					<div v-else>
						<p class="text-sm text-gray-700">
							No benches available for install
						</p>
					</div>
					<template v-slot:actions>
						<Button type="primary" route="/benches/new">New Bench</Button>
					</template>
				</Card>
			</div>
		</div>

		<Dialog
			v-model="showPlanSelectionDialog"
			title="Select app plan"
			width="half"
			:dismissable="true"
		>
			<ChangeAppPlanSelector
				v-if="marketplaceApp"
				:app="marketplaceApp"
				class="mb-9"
				@change="plan => (selectedPlan = plan.name)"
			/>

			<ErrorMessage :error="$resourceErrors" />

			<template v-slot:actions>
				<Button
					type="primary"
					:loading="$resources.installAppOnSite.loading"
					@click="installAppOnSite(selectedSite)"
					>Proceed</Button
				>
			</template>
		</Dialog>
	</div>
</template>

<script>
import ChangeAppPlanSelector from '@/components/ChangeAppPlanSelector.vue';

export default {
	name: 'InstallMarketplaceApp',
	props: ['marketplaceApp'],
	data() {
		return {
			showPlanSelectionDialog: false,
			selectedSite: null,
			selectedBench: null,
			selectedPlan: null
		};
	},
	components: {
		ChangeAppPlanSelector
	},
	resources: {
		optionsForQuickInstall() {
			return {
				method: 'press.api.marketplace.options_for_quick_install',
				params: {
					marketplace_app: this.marketplaceApp
				},
				auto: true
			};
		},
		addAppToBench() {
			return {
				method: 'press.api.bench.add_app',
				onSuccess() {
					this.$notify({
						title: 'App added successfully!',
						icon: 'check',
						color: 'green'
					});

					this.$router.push(`/benches/${this.selectedBench}/overview`);
				}
			};
		},
		installAppOnSite() {
			return {
				method: 'press.api.site.install_app',
				validate() {
					if (this.showPlanSelectionDialog && !this.selectedPlan) {
						return 'Please select a plan to continue';
					}
				},
				onSuccess() {
					this.$notify({
						title: 'App installed successfully!',
						icon: 'check',
						color: 'green'
					});

					this.selectedPlan = null;
					this.selectedSite = null;
					this.showPlanSelectionDialog = false;
					this.$resources.optionsForQuickInstall.fetch();
				}
			};
		}
	},
	methods: {
		addAppToBench(group) {
			this.selectedBench = group.name;

			this.$resources.addAppToBench.submit({
				name: group.name,
				source: group.source,
				app: this.options.app_name
			});
		},

		installAppOnSite(site) {
			this.selectedSite = site;

			// If paid app, show plan selection dialog
			if (this.options.has_plans_available && !this.showPlanSelectionDialog) {
				this.showPlanSelectionDialog = true;
				return;
			}

			this.$resources.installAppOnSite.submit({
				name: site,
				app: this.options.app_name,
				plan: this.selectedPlan
			});
		}
	},
	computed: {
		options() {
			if (
				this.$resources.optionsForQuickInstall.data &&
				!this.$resources.optionsForQuickInstall.loading
			) {
				return this.$resources.optionsForQuickInstall.data;
			}

			return null;
		}
	}
};
</script>
