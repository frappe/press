<template>
	<div class="pt-4">
		<PageHeader>
			<h1 slot="title">Sites</h1>
			<div class="flex items-center" slot="actions">
				<Button route="/sites/new" type="primary" iconLeft="plus">
					New Site
				</Button>
			</div>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div
				class="p-24 text-center"
				v-if="$resources.sites.data && $resources.sites.data.length === 0"
			>
				<div class="text-xl text-gray-800">
					You haven't created any sites yet.
				</div>
				<Button route="/sites/new" class="mt-10" type="primary">
					Create your first Site
				</Button>
			</div>
			<div v-else>
				<div
					class="grid items-center grid-cols-2 gap-12 py-4 text-sm text-gray-700 border-b md:grid-cols-4"
				>
					<span>Site Name</span>
					<span class="text-right md:text-center">Status</span>
					<span class="hidden text-right md:inline">Last Updated</span>
					<span class="hidden md:inline"></span>
				</div>
				<a
					class="grid items-center grid-cols-2 gap-12 py-4 text-base border-b md:grid-cols-4 hover:bg-gray-50 focus:outline-none focus:shadow-outline"
					v-for="site in $resources.sites.data"
					:key="site.name"
					:href="'#/sites/' + site.name"
				>
					<span class="">{{ site.name }}</span>
					<span class="text-right md:text-center">
						<Badge :status="site.status" />
					</span>
					<FormatDate class="hidden text-right md:block" type="relative">
						{{ site.modified }}
					</FormatDate>
					<span class="hidden text-right md:inline">
						<Badge
							:status="'Update Available'"
							v-if="site.update_available"
							class="mr-4"
						/>
						<a
							v-if="site.status === 'Active' || site.status === 'Updating'"
							:href="`https://${site.name}`"
							target="_blank"
							class="inline-flex items-baseline text-sm text-blue-500 hover:underline"
							>Visit Site<FeatherIcon
								name="external-link"
								class="w-3 h-3 ml-1"
							/>
						</a>
					</span>
				</a>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Sites',
	resources: {
		sites: 'press.api.site.all'
	},
	mounted() {
		this.setupSocketListener();
	},
	methods: {
		setupSocketListener() {
			if (this._socketSetup) return;
			this._socketSetup = true;

			this.$socket.on('agent_job_update', data => {
				if (data.name === 'New Site' || data.name === 'New Site from Backup') {
					if (data.status === 'Success') {
						this.$resources.sites.reload();
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
					this.$resources.sites.reload();
				}
			});
		},
		relativeDate(dateString) {
			return dateString;
		}
	}
};
</script>
