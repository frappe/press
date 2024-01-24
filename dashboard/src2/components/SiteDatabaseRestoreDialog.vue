<template>
	<Dialog
		:options="{
			title: 'Restore',
			actions: [
				{
					label: 'Restore',
					variant: 'solid',
					loading: $resources.restoreBackup.loading,
					onClick: () => $resources.restoreBackup.submit()
				}
			]
		}"
		v-model="showRestoreDialog"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<p class="text-base">Restore your database using a previous backup.</p>
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
				private: null
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
						return 'Please upload database, public and private files to restore.';
					}
				},
				onSuccess() {
					this.selectedFiles = {};
					this.$router.push({
						name: 'Site Detail Jobs',
						params: { objectType: 'Site', name: this.site }
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
