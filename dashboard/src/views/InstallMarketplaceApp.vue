<template>
	<div class="px-4 py-4 text-base sm:px-8">
		<Button v-if="$resources.opionsForQuickInstall" :loading="true"
			>Loading</Button
		>
		<div v-else>
			<h1 class="mb-4 text-xl font-semibold">
				Install App: {{ options ? options.title : marketplaceApp }}
			</h1>

			<div v-if="options" class="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
				<Card title="Sites" subtitle="Select a site to install">
					<div v-if="options.sites?.length">
						<button
							v-for="site in options.sites"
							class="block rounded-md py-2 px-1 text-base hover:bg-gray-50"
							@click="installAppOnSite(site)"
						>
							{{ site }}
						</button>
					</div>

					<div v-else>
						<p class="text-sm text-gray-700">No site available for install</p>
					</div>

					<Button class="mt-3" type="primary" route="/sites/new"
						>Create New Site</Button
					>
				</Card>

				<Card title="Private Benches" subtitle="Select a bench to install">
					<div v-if="options.release_groups?.length" class="space-y-3">
						<li
							v-for="bench in options.release_groups"
							class="flex w-full flex-row justify-between rounded-md py-2 px-1 text-left text-base hover:bg-gray-50"
						>
							<p>
								{{ bench.title }}
							</p>
							<Button
								@click="addAppToBench(bench)"
								:loading="$resources.addAppToBench.loading"
								>Add</Button
							>
						</li>

						<li
							v-for="bench in options.release_groups"
							class="flex w-full flex-row justify-between rounded-md py-2 px-1 text-left text-base hover:bg-gray-50"
						>
							<p>
								{{ bench.title }}
							</p>
							<Button @click="addAppToBench(bench)">Add</Button>
						</li>
					</div>

					<div v-else>
						<p class="text-sm text-gray-700">
							No benches available for install
						</p>
					</div>

					<Button class="mt-3" type="primary" route="/benches/new"
						>Create New Bench</Button
					>
				</Card>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'InstallMarketplaceApp',
	props: ['marketplaceApp'],
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
					this.$resources.optionsForQuickInstall.fetch();
				}
			};
		},
		installAppOnSite() {
			return {
				method: 'press.api.site.install_app'
			};
		}
	},
	methods: {
		addAppToBench(group) {
			console.log('Installing app on bench: ', group);
			this.$resources.addAppToBench.submit({
				name: group.name,
				source: group.source,
				app: this.options.app_name
			});
		},

		installAppOnSite(site) {
			// name: site name
			// press.api.site.install_app(name, app, plan=None)
			console.log('Installing app on site: ', site);
			this.$resources.installAppOnSite({
				name: site,
				app: options.app_name
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
