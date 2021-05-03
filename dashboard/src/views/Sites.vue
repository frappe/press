<template>
	<div class="pb-20 mt-8">
		<div class="px-4 sm:px-8">
			<div
				class="p-24 text-center"
				v-if="$resources.groups.data && $resources.groups.data.length === 0"
			>
				<div class="text-xl text-gray-800">
					You haven't created any sites yet.
				</div>
				<Button route="/sites/new" class="mt-10" type="primary">
					Create your first Site
				</Button>
			</div>
			<div class="space-y-8" v-else>
				<div v-for="group in groups" :key="group.name">
					<PageHeader class="mb-2 -mx-4 sm:-mx-8">
						<h2 slot="title">
							{{ getGroupTitle(group) }}
						</h2>
						<div class="flex items-center space-x-2" slot="actions">
							<Button
								v-if="!group.public && group.owned_by_team"
								:route="`/benches/${group.name}`"
							>
								Manage Bench
							</Button>
							<Button
								:route="
									`/sites/new${!group.public ? `?bench=${group.name}` : ''}`
								"
								type="primary"
								iconLeft="plus"
								v-if="group.public || (!group.public && group.owned_by_team)"
							>
								New Site
							</Button>
						</div>
					</PageHeader>
					<template v-if="group.sites.length">
						<router-link
							class="grid items-center grid-cols-2 gap-12 py-4 text-base border-b md:grid-cols-4 hover:bg-gray-50 focus:outline-none focus:shadow-outline"
							v-for="site in group.sites"
							:key="site.name"
							:to="'/sites/' + site.name"
						>
							<span class="">{{ site.name }}</span>
							<span class="text-right md:text-center">
								<Badge v-bind="siteStatus(site)" />
							</span>
							<FormatDate class="hidden text-right md:block" type="relative">
								{{ site.creation }}
							</FormatDate>
							<span class="hidden text-right md:inline">
								<Badge
									v-if="
										(site.status === 'Active' ||
											site.status === 'Inactive' ||
											site.status === 'Suspended') &&
											site.update_available
									"
									:status="'Update Available'"
									class="mr-4"
								/>
								<a
									v-if="site.status === 'Active' || site.status === 'Updating'"
									:href="`https://${site.name}`"
									target="_blank"
									class="inline-flex items-baseline text-sm text-blue-500 hover:underline"
									@click.stop
								>
									Visit Site
									<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
								</a>
							</span>
						</router-link>
					</template>
					<div class="text-base text-gray-600" v-else>
						No sites in this bench
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Sites',
	resources: {
		groups: 'press.api.site.all'
	},
	mounted() {
		this.setupSocketListener();
	},
	computed: {
		groups() {
			if (!this.$resources.groups.data) return [];

			let sharedBench = {
				name: 'shared-bench',
				title: 'Shared Bench',
				public: true,
				sites: []
			};
			this.$resources.groups.data
				.filter(group => !group.owned_by_team)
				.forEach(group => {
					sharedBench.sites = sharedBench.sites.concat(group.sites);
				});

			return [
				sharedBench,
				...this.$resources.groups.data.filter(group => group.owned_by_team)
			];
		}
	},
	methods: {
		setupSocketListener() {
			if (this._socketSetup) return;
			this._socketSetup = true;

			this.$socket.on('agent_job_update', data => {
				if (data.name === 'New Site' || data.name === 'New Site from Backup') {
					if (data.status === 'Success') {
						this.$resources.groups.reload();
						this.$notify({
							title: 'Site creation complete!',
							message: 'Login to your site and complete the setup wizard',
							icon: 'check',
							color: 'green'
						});
					}
				}
			});

			this.$socket.on('list_update', ({ doctype }) => {
				if (doctype === 'Site') {
					this.$resources.groups.reload();
				}
			});
		},
		getGroupTitle(group) {
			let privateBenches = (this.$resources.groups.data || []).filter(
				group => !group.public
			);
			if (privateBenches.length === 0) {
				return 'Sites';
			}
			return group.title;
		},
		relativeDate(dateString) {
			return dateString;
		},
		siteStatus(site) {
			let status = site.status;
			let color;
			let usage = Math.max(
				site.current_cpu_usage,
				site.current_database_usage,
				site.current_disk_usage
			);

			if (usage && usage >= 80 && status == 'Active') {
				color = 'yellow';
				status = 'Attention Required';
			}
			if (site.trial_end_date) {
				color = 'yellow';
				status = 'Trial';
			}
			return {
				status,
				color
			};
		}
	}
};
</script>
