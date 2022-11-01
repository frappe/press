<template>
	<div
		class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
	>
		<div
			class="py-2 text-base text-gray-600 sm:px-2"
			v-if="servers.length === 0"
		>
			No servers
		</div>
		<div class="py-2" v-for="(server, index) in servers" :key="server.name">
			<div class="flex items-center justify-between">
				<router-link
					:to="`/servers/${server.name}/overview`"
					class="block w-full rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between">
						<div class="text-base sm:w-4/12">
							{{ server.title }}
						</div>
						<div class="text-base sm:w-3/12">
							<Badge class="pointer-events-none" v-bind="serverBadge(server)" />
						</div>
						<div class="hidden w-2/12 text-sm text-gray-600 sm:block">
							Created {{ formatDate(server.creation, 'relative') }}
						</div>
					</div>
				</router-link>

				<div class="text-right text-base">
					<Dropdown
						v-if="server.status === 'Active' || server.status === 'Updating'"
						:items="dropdownItems(server)"
						right
					>
						<template v-slot="{ toggleDropdown }">
							<Button icon="more-horizontal" @click.stop="toggleDropdown()" />
						</template>
					</Dropdown>
					<div v-else class="h-[30px] w-[30px]"></div>
				</div>
			</div>
			<div
				class="translate-y-2 transform"
				:class="{ 'border-b': index < servers.length - 1 }"
			/>
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
		serverBadge(server) {
			let status = server.status;
			let color = null;
			return {
				color,
				status
			};
		},
		dropdownItems(server) {
			return [
				{
					label: 'Visit Server',
					action: () => {
						window.open(`https://${server.name}`, '_blank');
					}
				},
				{
					label: 'New Bench',
					action: () => {
						this.$router.push(`/servers/${server.name}/bench/new`);
					}
				}
			];
		}
	}
};
</script>
