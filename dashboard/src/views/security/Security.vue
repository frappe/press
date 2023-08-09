<template>
	<div>
		<SectionHeader class="mx-5 mt-8" :heading="getServerFilterHeading()">
			<template #actions>
				<Dropdown :options="serverFilterOptions()">
					<template v-slot="{ open }">
						<Button
							:class="[
								'rounded-md px-3 py-1 text-base font-medium',
								open ? 'bg-gray-200' : 'bg-gray-100'
							]"
							icon-left="chevron-down"
							>{{ serverFilter.replace('tag:', '') }}</Button
						>
					</template>
				</Dropdown>
			</template>
		</SectionHeader>
		<div class="mt-3 mx-5">
			<LoadingText v-if="$resources.allServers.loading" />
			<ServerList v-else :servers="servers" />
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
			serverFilter: 'All Servers'
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
		}
	}
};
</script>
