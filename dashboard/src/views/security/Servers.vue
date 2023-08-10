<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs :items="[{ label: 'Security', route: '/security' }]">
			</BreadCrumbs>
		</header>
		<div>
			<div class="mx-5 mt-5">
				<div class="flex">
					<div class="flex w-full space-x-2 pb-4">
						<FormControl label="Search Servers" v-model="searchTerm">
							<template #prefix>
								<FeatherIcon name="search" class="w-4 text-gray-600" />
							</template>
						</FormControl>
						<FormControl
							label="Server Type"
							class="mr-8"
							type="select"
							:options="serverTypeFilterOptions()"
							v-model="serverFilter.server_type"
						/>
					</div>
				</div>
				<LoadingText v-if="$resources.allServers.loading" />
				<div v-else>
					<div class="flex">
						<div class="flex w-full px-3 py-4">
							<div class="w-4/12 text-base font-medium text-gray-900">
								Server Name
							</div>
							<div class="w-2/12 text-base font-medium text-gray-900">
								Security Updates
							</div>
						</div>
					</div>
					<div class="w-8" />
				</div>
				<div class="mx-2.5 border-b" />
				<ServerList :servers="servers" />
			</div>
		</div>
	</div>
</template>

<script>
import ServerList from '@/views/security/ServerList.vue';
export default {
	name: 'SecurityUpdates',
	components: {
		ServerList
	},
	data() {
		return {
			searchTerm: '',
			serverFilter: {
				server_type: 'All Servers',
				tag: ''
			}
		};
	},
	resources: {
		allServers() {
			return {
				method: 'press.api.security.get_servers',
				params: { server_filter: this.serverFilter },
				auto: true
			};
		}
	},
	computed: {
		servers() {
			if (!this.$resources.allServers.data) {
				return [];
			}
			return this.$resources.allServers.data;
		}
	},
	methods: {
		getServerFilterHeading() {
			return this.serverFilter;
		},
		serverFilterOptions() {
			const options = [
				{
					group: 'Types',
					items: [
						{
							label: 'All Servers',
							onClick: () => (this.serverFilter = 'All Servers')
						},
						{
							label: 'App Servers',
							onClick: () => (this.serverFilter = 'App Servers')
						},
						{
							label: 'Database Servers',
							onClick: () => (this.serverFilter = 'Database Servers')
						}
					]
				}
			];

			return options;
		},
		serverTypeFilterOptions() {
			return [
				{
					label: 'All Servers',
					value: 'All Servers'
				},
				{
					label: 'App Servers',
					value: 'App Servers'
				},
				{
					label: 'Database Servers',
					value: 'Database Servers'
				}
			];
		}
	}
};
</script>
