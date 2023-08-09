<template>
	<div>
		<div
			class="py-2 text-base text-gray-600 sm:px-2"
			v-if="servers.length === 0"
		>
			No servers
		</div>
		<div v-for="(server, index) in servers" :key="server.name">
			<div class="flex items-center rounded hover:bg-gray-100">
				<router-link
					:to="{ name: 'ServerOverview', params: { serverName: server.name } }"
					class="w-full px-3 py-4"
				>
					<div class="flex items-center">
						<div class="w-4/12">
							<div class="truncate text-base font-medium" :title="server.name">
								{{ server.name }}
							</div>
						</div>
						<div class="w-2/12">
							<Badge
								class="pointer-events-none"
								variant="subtle"
								:label="server.status"
							/>
						</div>
						<div class="w-2/12">
							<img
								v-if="server.region_info.image"
								class="h-4"
								:src="server.region_info.image"
								:alt="`Flag of ${server.region_info.title}`"
								:title="server.region_info.image"
							/>
							<span class="text-base text-gray-700" v-else>
								{{ server.region_info.title }}
							</span>
						</div>
						<div class="w-1/12">
							<div class="text-base text-gray-700">
								{{
									server.plan
										? `${$planTitle(server.plan)}${
												server.plan.price_usd > 0 ? '/mo' : ''
										  }`
										: 'No Plan Set'
								}}
							</div>
						</div>
					</div>
				</router-link>
				<Dropdown :options="dropdownItems(server)">
					<template v-slot="{ open }">
						<Button variant="ghost" class="mr-2" icon="more-horizontal" />
					</template>
				</Dropdown>
			</div>
			<div v-if="index < servers.length - 1" class="mx-2.5 border-b" />
		</div>
	</div>
</template>
<script>
export default {
	name: 'ServerList',
	props: ['servers'],
	data() {
		return {
			errorMessage: null
		};
	},
	resources: {},
	methods: {
		dropdownItems(server) {
			return [
				{
					label: 'Visit Server',
					onClick: () => {
						window.open(`https://${server.name}`, '_blank');
					}
				},
				{
					label: 'New Bench',
					onClick: () => {
						this.$router.push(`/servers/${server.app_server}/bench/new`);
					}
				}
			];
		}
	}
};
</script>
