<template>
	<div class="py-2 text-base text-gray-600 sm:px-2" v-if="servers.length === 0">
		No servers
	</div>
	<div v-for="(server, index) in servers" :key="server.name">
		<div class="flex items-center rounded hover:bg-gray-100">
			<router-link
				:to="{ name: 'SecurityOverview', params: { serverName: server.name } }"
				class="w-full px-3 py-4"
			>
				<div class="flex items-center">
					<div class="sm:w-4/12">
						<div class="truncate text-base font-medium" :title="server.name">
							{{ server.name }}
						</div>
					</div>
					<div class="w-2/12">
						<Badge
							class="pointer-events-none"
							variant="subtle"
							:label="server.security_updates_status"
							:theme="getColor(server.security_updates_status)"
						/>
					</div>
				</div>
			</router-link>
			<Dropdown :options="dropdownItems(server)">
				<template v-slot="{ open }">
					<Button variant="ghost" class="mr-2" icon="more-horizontal" />
				</template>
			</Dropdown>
		</div>
		<div
			class="translate-y-2 transform"
			:class="{ 'border-b': index < servers.length - 1 }"
		/>
	</div>
</template>
<script>
export default {
	name: 'ServerList',
	props: ['servers'],

	methods: {
		getColor(security_updates_status) {
			if (security_updates_status === 'Up to date') {
				return 'green';
			}

			return 'red';
		},
		dropdownItems(server) {
			return [
				{
					label: 'View Security Updates',
					onClick: () => {
						this.$router.push(`/security/${server.name}/security_update`);
					}
				},
				{
					label: 'Manage Firewall',
					onClick: () => {
						this.$router.push(`/security/${server.app_server}/firewall`);
					}
				},
				{
					label: 'SSH Sessions',
					onClick: () => {
						this.$router.push(`/security/${server.app_server}/ssh_session`);
					}
				}
			];
		}
	}
};
</script>
