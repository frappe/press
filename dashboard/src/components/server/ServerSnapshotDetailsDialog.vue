<template>
	<Dialog v-model="show" :options="{ title: `Snapshot Details`, size: '2xl' }">
		<template #body-content>
			<div class="flex flex-col space-y-4">
				<!-- Meta -->
				<div class="flex flex-row justify-between">
					<div>
						<p class="text-xs text-gray-600">Status</p>
						<p class="mt-2 text-sm text-gray-700">
							{{ snapshot?.status }}
						</p>
					</div>
					<div>
						<p class="text-xs text-gray-600">Progress</p>
						<p class="mt-2 text-sm text-gray-700">{{ snapshot?.progress }}%</p>
					</div>
					<div>
						<p class="text-xs text-gray-600">Mode</p>
						<p class="mt-2 text-sm text-gray-700">
							{{ snapshot.consistent ? 'Consistent' : 'Inconsistent' }}
						</p>
					</div>
					<div>
						<p class="text-xs text-gray-600">Cost</p>
						<p class="mt-2 text-sm text-gray-700">
							{{ snapshot?.free ? 'Free' : 'Chargable' }}
						</p>
					</div>
					<div>
						<p class="text-xs text-gray-600">Size</p>
						<p class="mt-2 text-sm text-gray-700">
							{{ snapshot?.total_size_gb ? snapshot.total_size_gb : '--' }} GB
						</p>
					</div>
				</div>
				<!-- Server -->
				<div class="overflow-hidden rounded-md border border-gray-300">
					<table class="min-w-full">
						<thead class="bg-surface-gray-2">
							<tr>
								<th
									class="px-4 py-2 text-left text-sm font-medium text-gray-700 border-b"
								></th>
								<th
									class="px-4 py-2 text-left text-sm font-medium text-gray-700 border-b"
								>
									App Server
								</th>
								<th
									class="px-4 py-2 text-left text-sm font-medium text-gray-700 border-b"
								>
									Database Server
								</th>
							</tr>
						</thead>
						<tbody>
							<tr>
								<td>Name</td>
								<td>{{ snapshot?.app_server_title }}</td>
								<td>{{ snapshot?.database_server_title }}</td>
							</tr>
							<tr>
								<td>ID</td>
								<td>{{ snapshot?.app_server_hostname }}</td>
								<td>{{ snapshot?.database_server_hostname }}</td>
							</tr>
							<tr>
								<td>Consistent</td>
								<td>{{ snapshot?.consistent ? 'Yes' : 'No' }}</td>
								<td>{{ snapshot?.consistent ? 'Yes' : 'No' }}</td>
							</tr>
							<tr>
								<td>Progress</td>
								<td>{{ snapshot?.app_server_snapshot_progress }}%</td>
								<td>{{ snapshot?.database_server_snapshot_progress }}%</td>
							</tr>
							<tr>
								<td>Size</td>
								<td>{{ snapshot?.app_server_snapshot_size }} GB</td>
								<td>{{ snapshot?.database_server_snapshot_size }} GB</td>
							</tr>
							<tr>
								<td>Timestamp</td>
								<td>
									{{
										$format.utcDate(
											snapshot?.app_server_snapshot_start_time,
											'llll',
										)
									}}
								</td>
								<td>
									{{
										$format.utcDate(
											snapshot?.database_server_snapshot_start_time,
											'llll',
										)
									}}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<!-- Site List -->
				<div>
					<!-- Collapsable Button -->
					<div
						class="flex flex-row items-center gap-1 cursor-pointer"
						@click="showSiteList = !showSiteList"
					>
						<Button
							variant="ghost"
							:icon="showSiteList ? 'chevron-down' : 'chevron-right'"
						>
							{{ showSiteList ? 'Show Less' : 'Show All' }}
						</Button>

						<div class="flex flex-row items-center gap-1">
							<p class="text-sm font-medium text-gray-800">
								{{ sites.length }} Site{{ sites.length > 1 ? 's' : '' }}
								Recoverable
							</p>
						</div>
					</div>
					<!-- list -->
					<div class="flex flex-col mt-2 px-2 gap-1.5" v-if="showSiteList">
						<span
							v-for="site in snapshot?.site_list_json ?? []"
							class="text-sm text-gray-800"
						>
							-> {{ site }}
						</span>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Checkbox } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';
import { confirmDialog, icon } from '../../utils/components';
import ServerSnapshotRecoveryDetails from './ServerSnapshotRecoveryDetails.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'ServerSnapshotDetailsDialog',
	components: {
		Checkbox,
		ObjectList,
		ServerSnapshotRecoveryDetails,
	},
	props: {
		name: {
			type: String,
			required: true,
		},
	},
	data() {
		return {
			show: true,
			showSiteList: false,
			showRecoverSitePrompt: false,
			selectedSitesForRecovery: [],
			selectedSnapshotRecoveryId: null,
		};
	},
	resources: {
		snapshot() {
			return {
				type: 'document',
				doctype: 'Server Snapshot',
				name: this.name,
				auto: true,
			};
		},
	},
	computed: {
		snapshot() {
			return this.$resources.snapshot?.doc || {};
		},
		sites() {
			return this.snapshot?.site_list_json || [];
		},
		sitesMapped() {
			return this.sites.map((site) => {
				return {
					name: site,
				};
			});
		},
	},
};
</script>

<style scoped>
td {
	@apply px-4 py-2 border-b text-sm text-gray-800;
}

tbody tr:last-child td {
	@apply border-b-0;
}
</style>
