<template>
	<Card title="Server Info" subtitle="General information about your server">
		<div class="divide-y">
			<div class="flex items-center py-3">
				<Avatar
					v-if="info.owner"
					:imageURL="info.owner.user_image"
					:label="info.owner.first_name"
				/>
				<div class="ml-3 flex flex-1 items-center justify-between">
					<div>
						<div class="text-base text-gray-600">Owned By</div>
						<div class="text-base font-medium text-gray-900">
							{{ info.owner.first_name }}
							{{ info.owner.last_name }}
						</div>
					</div>
					<div class="text-right">
						<div class="text-base text-gray-600">Created On</div>
						<div class="text-base font-medium text-gray-900">
							{{ formatDate(info.created_on, 'DATE_FULL') }}
						</div>
					</div>
					<div v-if="info.last_deployed" class="text-right">
						<div class="text-base text-gray-600">Last Deployed</div>

						<div class="text-base font-medium text-gray-900">
							{{
								$date(info.last_deployed).toLocaleString({
									month: 'long',
									day: 'numeric'
								})
							}}
						</div>
					</div>
				</div>
			</div>

			<ListItem
				v-if="server.status !== 'Pending'"
				title="Drop Server"
				description="Once you drop server your server, there is no going back"
			>
				<template v-slot:actions>
					<ServerDrop :server="server" v-slot="{ showDialog }">
						<Button @click="showDialog">
							<span class="text-red-600">Drop Server</span>
						</Button>
					</ServerDrop>
				</template>
			</ListItem>
		</div>
	</Card>
</template>
<script>
import ServerDrop from './ServerDrop.vue';
export default {
	name: 'ServerOverviewInfo',
	props: ['server', 'info'],
	components: { ServerDrop },
	data() {
		return {
			loading: false
		};
	}
};
</script>
