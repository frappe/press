<template>
	<Dialog
		v-model="show"
		:options="{ title: 'Recover Sites From Snapshot', size: '2xl' }"
	>
		<template #body-content>
			<div class="flex flex-col">
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
					<div class="w-full">
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
						<p class="text-base">Recovery Details</p>
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
