<template>
	<Dialog
		v-model="show"
		:options="{ title: `Snapshot(${name}) Details`, size: '2xl' }"
	>
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
							{{ snapshot?.total_size_gb }} GB
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
							@click="showSiteList = !showSiteList"
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
					<div class="flex flex-col mt-2 px-2" v-if="showSiteList">
						<span
							v-for="site in snapshot?.site_list_json ?? []"
							class="text-sm text-gray-800"
						>
							-> {{ site }}
						</span>
					</div>
				</div>

				<!-- Delete option -->
				<AlertBanner
					v-if="!snapshot?.free"
					title="Delete this snapshot to avoid further charges"
					type="warning"
					:showIcon="false"
				>
					<Button
						class="ml-auto"
						iconLeft="trash-2"
						variant="solid"
						theme="red"
						size="sm"
						:loading="$resources.snapshot?.deleteSnapshots?.loading"
						@click="deleteSnapshot()"
					>
						Delete
					</Button>
				</AlertBanner>

				<!-- Recover Site Prompt -->
				<div v-if="showRecoverSitePrompt" class="w-full flex flex-col">
					<div class="flex flex-row gap-2 items-center mb-4">
						<Button
							icon="chevron-left"
							variant="outline"
							@click="showRecoverSitePrompt = false"
							>Back</Button
						>
						<p class="text-base">Select Sites to Recover</p>
					</div>
					<div>
						<p
							class="rounded mb-4 p-2 text-sm text-gray-700 bg-gray-100 border"
						>
							Frappe Cloud will start temporary servers from the snapshot and
							<b>backup the selected sites from the snapshot</b>. You will be
							able to download the backup files for next <b>48 hours</b> once
							the recovery gets completed. <br /><br />
							You <b>will not be charged</b> for this recovery process.
						</p>
					</div>
					<div>
						<GenericList
							:options="availableSitesForRecoveryOptions"
							@update:selections="handleSitesSelection"
						/>
					</div>
					<ErrorMessage
						class="mt-2"
						:message="$resources.snapshot.recoverSites.error"
					/>
					<Button
						class="mt-4 w-full"
						theme="gray"
						variant="solid"
						:disabled="selectedSitesForRecovery.length < 1"
						:loading="$resources.snapshot.recoverSites.loading"
						@click="recoverSites"
						>Recover Site & Backup</Button
					>
				</div>
				<!-- Server Snapshot Recovery Details -->
				<div v-else-if="selectedSnapshotRecoveryId">
					<div class="flex flex-row gap-2 items-center mb-4">
						<Button
							icon="chevron-left"
							variant="outline"
							@click="selectedSnapshotRecoveryId = null"
							>Back</Button
						>
						<p class="text-base">
							Snapshot Recovery ({{ selectedSnapshotRecoveryId }}) Details
						</p>
					</div>
					<ServerSnapshotRecoveryDetails :name="selectedSnapshotRecoveryId" />
				</div>
				<!-- Recovery List -->
				<ObjectList v-else :options="snapshotRecoveryOptions" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Checkbox } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';
import { date } from '../../utils/format';
import { confirmDialog, icon } from '../../utils/components';
import RestoreSnapshotIcon from '~icons/lucide/database-backup';
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
				whitelistedMethods: {
					lock: 'lock',
					unlock: 'unlock',
					recoverSites: 'recover_sites',
					deleteSnapshots: 'delete_snapshots',
				},
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
		snapshotRecoveryOptions() {
			return {
				doctype: 'Server Snapshot Recovery',
				filters: {
					snapshot: this.name,
				},
				fields: ['name', 'status', 'creation'],
				orderBy: 'creation desc',
				columns: [
					{
						label: 'Timestamp',
						fieldname: 'creation',
						width: 0.5,
						type: 'Text',
						format(value) {
							return date(value, 'llll');
						},
					},
					{
						label: 'Record ID',
						fieldname: 'name',
						width: 0.2,
						type: 'Text',
						align: 'left',
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: 0.3,
						type: 'Badge',
						align: 'center',
					},
				],
				primaryAction: ({ documentResource: record }) => {
					return {
						label: 'Recover Sites',
						slots: {
							prefix: icon(RestoreSnapshotIcon),
						},
						onClick: () => {
							this.showRecoverSitePrompt = true;
							this.selectedSitesForRecovery = [];
						},
					};
				},
				onRowClick: (record) => {
					this.selectedSnapshotRecoveryId = record.name;
				},
			};
		},
		sitesMapped() {
			return this.sites.map((site) => {
				return {
					name: site,
				};
			});
		},
		availableSitesForRecoveryOptions() {
			return {
				data: this.sitesMapped,
				selectable: true,
				columns: [
					{
						label: 'Site',
						fieldname: 'name',
						width: 1,
						type: 'Text',
					},
				],
			};
		},
	},
	methods: {
		handleSitesSelection(data) {
			this.selectedSitesForRecovery = Array.from(data);
		},
		recoverSites() {
			toast.promise(
				this.$resources.snapshot.recoverSites.submit({
					sites: this.selectedSitesForRecovery,
				}),
				{
					loading: 'Requesting snapshot recovery...',
					success: () => {
						this.showRecoverSitePrompt = false;
						this.selectedSitesForRecovery = [];
						return 'Snapshot recovery request submitted successfully';
					},
					error: 'Failed to request snapshot recovery',
				},
			);
		},
		deleteSnapshot() {
			confirmDialog({
				title: 'Delete Snapshot',
				message:
					'Are you sure you want to delete this snapshot? This will delete the snapshot and all associated data.',
				primaryAction: {
					label: 'Delete',
				},
				onSuccess: ({ hide }) => {
					if (this.$resources.snapshot.deleteSnapshots.loading) return;
					toast.promise(
						this.$resources.snapshot.deleteSnapshots.submit(
							{},
							{
								onSuccess() {
									hide();
									this.show = false;
								},
							},
						),
						{
							loading: 'Deleting snapshot...',
							success: 'Snapshot deleted successfully',
							error: 'Failed to delete snapshot',
						},
					);
				},
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
