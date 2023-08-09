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
					:to="`/servers/${server.name}/security_overview`"
					class="mr-1 block w-full rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between">
						<div class="text-base sm:w-4/12">
							{{ server.title }}
						</div>
						<div class="text-base sm:w-3/12">
							<Badge class="pointer-events-none" :label="server.status" />
						</div>
						<div class="text-base sm:w-3/12">
							<Badge
								class="pointer-events-none"
								variant="ghost"
								:label="server.security_updates_status"
								:theme="getColor(server.security_updates_status)"
							/>
						</div>
						<div class="hidden w-2/12 text-sm text-gray-600 sm:block">
							Created {{ formatDate(server.creation, 'relative') }}
						</div>
					</div>
				</router-link>
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

	methods: {
		getColor(security_updates_status) {
			if (security_updates_status === 'Up to date') {
				return 'green';
			}

			return 'red';
		}
	}
};
</script>
