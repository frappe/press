<template>
	<div
		class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
	>
		<div
			class="py-2 text-base text-gray-600 sm:px-2"
			v-if="servers && servers.length === 0"
		>
			No Code Servers
		</div>
		<div class="py-2" v-for="(server, index) in servers" :key="server.name">
			<div class="flex items-center justify-between">
				<router-link
					:to="`/codeservers/${server.name}/overview`"
					class="block w-full rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between">
						<div
							class="hover:text-ellipses truncate break-all text-base w-1/3 sm:w-4/12"
						>
							{{ server.name }}
						</div>
						<div class="text-base w-1/3 sm:w-4/12">
							<Badge
								class="ml-4 hidden md:inline-block"
								:label="server.status"
								:colorMap="$badgeStatusColorMap"
							></Badge>
						</div>
						<div class="text-base w-1/3 sm:w-4/12 hidden sm:block">
							<div class="hover:text-ellipses truncate break-all hover:w-full">
								{{ server.title }}
							</div>
						</div>
					</div>
				</router-link>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'CodeServersList',
	props: {
		servers: {
			type: Object,
			default: () => {}
		}
	}
};
</script>
