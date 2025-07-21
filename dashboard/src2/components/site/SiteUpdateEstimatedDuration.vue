<template>
	<Dialog
		:options="{ title: this.site, size: '2xl' }"
		v-model="showDialog"
		@after-leave="dialogClosed"
	>
		<template v-slot:body-content>
			<div
				class="flex h-[200px] w-full items-center justify-center gap-2 bg-white-overlay-900 text-base text-gray-800"
				v-if="this.$resources.options_for_site_update?.loading"
			>
				<Spinner class="w-4" /> Loading ...
			</div>

			<div v-else class="flex flex-col gap-4">
				<AlertBanner
					title="Durations are based on historical data and will be refined for better accuracy over time"
					type="warning"
					:showIcon="false"
				></AlertBanner>
				<div class="flex flex-col gap-2">
					<p class="text-base font-medium">Logical Backup</p>
					<GenericList
						:options="{
							data: [
								{
									task: 'Enable Maintenance Mode',
									duration: '5s ~ 5min',
								},
								{
									task: 'Backup Database',
									duration: `${formatSeconds(this.logicalBackupDuration)}`,
								},
								{
									task: 'Site Update & Migration',
									duration: 'Depends on update & site size',
								},
								{
									task: 'Wait time before Restoration [If Required]',
									duration: `~5s`,
								},
								{
									task: 'Restore Database [If Required]',
									duration: 'Depends on db size',
								},
							],
							columns: columns,
						}"
					/>
				</div>
				<Alert v-if="!eligibleForPhysicalBackup">
					<p class="text-base">
						Physical Backup is not enabled for your current site. <br />
						If your site database size is > 3GB, please reach out to
						support.frappe.io to check if it's possible to enable it.
					</p>
				</Alert>
				<div class="flex flex-col gap-2" v-if="eligibleForPhysicalBackup">
					<p class="text-base font-medium">Physical Backup</p>
					<GenericList
						:options="{
							data: [
								{
									task: 'Enable Maintenance Mode',
									duration: '5s ~ 5min',
								},
								{
									task: 'Backup Database',
									duration: `10s ~ 45s`,
								},
								{
									task: 'Site Update & Migration',
									duration: 'Depends on update & site size',
								},
								{
									task: 'Wait time before Restoration [If Required]',
									duration: `${formatSeconds(this.snapshotDuration)}`,
								},
								{
									task: 'Restore Database [If Required]',
									duration: 'Depends on db size',
								},
							],
							columns: columns,
						}"
					/>
				</div>

				<div class="flex flex-col gap-2" v-if="eligibleForPhysicalBackup">
					<p class="text-base font-medium">
						Physical Backup (Wait For Snapshot Before Update)
					</p>
					<GenericList
						:options="{
							data: [
								{
									task: 'Enable Maintenance Mode',
									duration: '5s ~ 5min',
								},
								{
									task: 'Backup Database',
									duration: `10s ~ 45s`,
								},
								{
									task: 'Wait for Snapshot',
									duration: `${formatSeconds(this.snapshotDuration)}`,
								},
								{
									task: 'Site Update & Migration',
									duration: 'Depends on update & site size',
								},
								{
									task: 'Wait time before Restoration [If Required]',
									duration: `~5s`,
								},
								{
									task: 'Restore Database [If Required]',
									duration: 'Depends on db size',
								},
							],
							columns: columns,
						}"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getToastErrorMessage } from '../../utils/toast';
import GenericList from '../GenericList.vue';
import { toast } from 'vue-sonner';
import AlertBanner from '../AlertBanner.vue';

export default {
	name: 'SiteUpdateEstimatedDuration',
	props: ['site'],
	components: {
		GenericList,
		AlertBanner,
	},
	data() {
		return {
			showDialog: true,
			columns: [
				{
					label: 'Task',
					fieldname: 'task',
					width: 0.8,
				},
				{
					label: 'Duration',
					fieldname: 'duration',
				},
			],
		};
	},
	methods: {
		dialogClosed() {
			this.showDialog = false;
		},
		formatSeconds(seconds) {
			if (seconds === -1) return 'Not enough data to estimate';
			if (!seconds) return '~0s';
			seconds = Math.round(seconds);
			if (seconds < 60) return `~${seconds}s`;
			const minutes = Math.floor(seconds / 60);
			const remainingSeconds = seconds % 60;

			if (minutes < 60) {
				return `~${minutes}mins ${remainingSeconds}s`;
			}
			const hours = Math.floor(minutes / 60);
			const remainingMinutes = minutes % 60;
			return `~${hours}hrs ${remainingMinutes}mins ${remainingSeconds}s`;
		},
	},
	computed: {
		eligibleForPhysicalBackup() {
			return (
				this.$resources.options_for_site_update.data?.message
					?.eligible_for_physical_backup || false
			);
		},
		logicalBackupDuration() {
			return (
				this.$resources.options_for_site_update.data?.message
					?.logical_backup_duration || 0
			);
		},
		snapshotDuration() {
			return (
				this.$resources.options_for_site_update.data?.message
					?.snapshot_duration || 0
			);
		},
	},
	resources: {
		options_for_site_update() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'options_for_site_update',
					};
				},
				auto: true,
				onError: (e) => {
					toast.error(
						getToastErrorMessage(
							e,
							'Failed to fetch site update estimated duration',
						),
					);
					this.showDialog = false;
				},
			};
		},
	},
};
</script>
