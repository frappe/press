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
				},
			],
		}"
		v-model="show"
		@close="resetValues"
	>
		<template #body-content>
			<div class="flex flex-col gap-3">
				<p
					class="text-md text-base text-gray-800"
					v-if="!this.$site?.doc?.allow_physical_backup_by_user"
				>
					Are you sure you want to backup your site ?
				</p>
				<AlertBanner
					v-if="this.$site?.doc?.allow_physical_backup_by_user"
					title="Backup can cause some downtime on your site. It depends on the size of your database."
					type="info"
					:showIcon="false"
				>
				</AlertBanner>
				<div v-if="this.$site?.doc?.allow_physical_backup_by_user">
					<FormControl
						variant="outline"
						type="checkbox"
						label="Physical Backup"
						v-model="isPhysical"
					>
					</FormControl>
				</div>

				<div v-if="this.$site?.doc?.allow_physical_backup_by_user">
					<FormControl
						variant="outline"
						type="checkbox"
						label="Backup Public & Private Files"
						v-model="includeFiles"
						:disabled="isPhysical"
					>
					</FormControl>

					<AlertBanner
						v-if="isPhysical"
						class="mt-2"
						title="Physical Backup can't backup your site's private and public files currently."
						type="warning"
						:showIcon="false"
					>
					</AlertBanner>
				</div>
			</div>
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
			isPhysical: false,
			includeFiles: true,
		};
	},
	watch: {
		isPhysical(newValue) {
			if (newValue == true) {
				this.includeFiles = false;
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
				physical: this.isPhysical,
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
