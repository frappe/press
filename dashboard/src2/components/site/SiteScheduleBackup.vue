<template>
	<Dialog
		:options="{
			title: 'Schedule Backup',
			actions: [
				{
					label: 'Schedule Backup',
					loading: this.site?.backup?.loading,
					variant: 'solid',
					onClick: scheduleBackup,
					disabled: backupDatabase == false,
				},
			],
		}"
		v-model="show"
		@close="resetValues"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<AlertBanner
					title="Backup can cause some downtime on your site. It depends on the size of your database."
					type="info"
					:showIcon="false"
				>
				</AlertBanner>
				<div>
					<FormControl
						variant="outline"
						type="checkbox"
						label="Backup Database"
						v-model="backupDatabase"
					>
					</FormControl>
				</div>

				<FormControl
					v-if="this.$site?.doc?.allow_physical_backup_by_user"
					variant="outline"
					type="select"
					label="Backup Type"
					v-model="selectedBackupType"
					:options="[
						{
							label: 'Logical',
							value: 'Logical',
						},
						{
							label: 'Physical',
							value: 'Physical',
						},
					]"
				>
				</FormControl>

				<div>
					<FormControl
						variant="outline"
						type="checkbox"
						label="Backup Public & Private Files"
						v-model="includeFiles"
						:disabled="selectedBackupType == 'Physical'"
					>
					</FormControl>

					<AlertBanner
						v-if="selectedBackupType == 'Physical'"
						class="mt-2"
						title="Physical Backup can't backup your site's private and public files currently."
						type="warning"
						:showIcon="false"
					>
					</AlertBanner>
				</div>
			</div>

			<!-- {{ this.$site?.doc?.allow_physical_backup_by_user }} -->
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { getToastErrorMessage } from '../../utils/toast';
import AlertBanner from '../AlertBanner.vue';

export default {
	props: ['site', 'onScheduleBackupSuccess'],
	components: {
		AlertBanner,
	},
	data() {
		return {
			show: true,
			selectedBackupType: 'Logical',
			includeFiles: true,
			backupDatabase: true,
		};
	},
	watch: {
		selectedBackupType(newValue) {
			if (newValue == 'Physical') {
				this.includeFiles = false;
			}
		},
		backupDatabase(newValue) {
			if (newValue == false) {
				toast.info('Database backup is mandatory.');
				setTimeout(() => (this.backupDatabase = true), 1000);
			}
		},
	},
	resources: {
		scheduleBackup() {
			return {};
		},
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
	},
	methods: {
		resetValues() {},
		scheduleBackup() {
			this.$router.push({
				name: 'Site Detail Backups',
				params: { name: this.$site.doc.name },
			});
			let site_backup_promise = this.$site.backup.submit({
				with_files: this.includeFiles,
				physical: this.selectedBackupType === 'Physical',
			});
			toast.promise(site_backup_promise, {
				loading: 'Scheduling backup...',
				success: () => {
					this.show = false;
					if (this.onScheduleBackupSuccess) {
						this.onScheduleBackupSuccess();
					} else {
						this.$router.push({
							name: 'Site Detail Backups',
							params: { name: this.$site.doc.name },
						});
					}
					return 'Backup scheduled successfully.';
				},
				error: (e) => getToastErrorMessage(e),
			});
		},
	},
};
</script>
