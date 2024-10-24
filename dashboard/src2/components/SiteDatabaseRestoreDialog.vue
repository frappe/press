<template>
	<Dialog
		:options="{
			title: 'Restore',
			actions: [
				{
					label: 'Restore',
					variant: 'solid',
					theme: 'red',
					loading: $resources.restoreBackup.loading,
					onClick: () => {
						$resources.restoreBackup.submit();
						showRestoreDialog = false;
					}
				}
			]
		}"
		v-model="showRestoreDialog"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<p class="text-base">Restore your database using a previous backup.</p>
				<div
					class="flex items-center rounded border border-gray-200 bg-gray-100 p-4 text-sm text-gray-600"
				>
					<i-lucide-alert-triangle class="mr-4 inline-block h-6 w-6" />
					<div>
						This operation will replace all <b>data</b> & <b>apps</b> in your
						site with those from the backup
					</div>
				</div>
				<BackupFilesUploader v-model:backupFiles="selectedFiles" />
			</div>
			<div class="mt-3">
				<!-- Skip Failing Checkbox -->
				<input
					id="skip-failing"
					type="checkbox"
					class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
					v-model="skipFailingPatches"
				/>
				<label for="skip-failing" class="ml-2 text-sm text-gray-900">
					Skip failing patches (if any patch fails)
				</label>
			</div>
			<ErrorMessage class="mt-2" :message="$resources.restoreBackup.error" />
		</template>
	</Dialog>
</template>
<script>
import { DashboardError } from '../utils/error';

export default {
	name: 'SiteDatabaseRestoreDialog',
	props: {
		site: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			showRestoreDialog: true,
			selectedFiles: {
				database: null,
				public: null,
				private: null,
				config: null
			},
			skipFailingPatches: false
		};
	},
	resources: {
		restoreBackup() {
			return {
				url: 'press.api.site.restore',
				params: {
					name: this.site,
					files: this.selectedFiles,
					skip_failing_patches: this.skipFailingPatches
				},
				validate() {
					if (!this.filesUploaded) {
						throw new DashboardError(
							'Please upload database, public and private files to restore.'
						);
					}
				},
				onSuccess() {
					this.selectedFiles = {};
					this.$router.push({
						name: 'Site Jobs',
						params: { name: this.site }
					});
				}
			};
		}
	},
	computed: {
		filesUploaded() {
			return this.selectedFiles.database;
		}
	}
};
</script>
