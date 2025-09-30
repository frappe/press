<template>
	<Dialog
		v-model="showRestoreDialog"
		:disableOutsideClickToClose="true"
		:options="{ title: 'Restore' }"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<p class="text-base">Restore your site using a previous backup.</p>
				<div
					class="flex items-center rounded border border-gray-200 bg-gray-100 p-4 text-sm text-gray-600"
				>
					<lucide-alert-triangle class="mr-4 inline-block h-6 w-6" />
					<div>
						This will overwrite all <b>data</b> & <b>apps</b> in your site with
						those from the backup
					</div>
				</div>
				<BackupFilesUploader
					ref="backupFilesUploader"
					v-model:backupFiles="selectedFiles"
					:site="this.site"
					:disableUploadButton="this.uploadingFiles"
					:onError="
						(errorMessage) => {
							this.errorMessageFromUploader = errorMessage;
							this.uploadingFiles = false;
						}
					"
					@uploadComplete="(files) => startRestore(files)"
					@abortUpload="(e) => failureHandler(e)"
				/>
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
			<ErrorMessage
				class="mt-2"
				:message="$resources.restoreBackup.error || errorMessageFromUploader"
			/>
		</template>
		<template v-slot:actions>
			<Button
				class="w-full"
				variant="solid"
				theme="red"
				:loading="$resources.restoreBackup.loading || uploadingFiles"
				@click="() => startUploadFiles()"
			>
				{{
					uploadingFiles
						? 'Uploading Files...'
						: $resources.restoreBackup.loading
							? 'Triggering Restore...'
							: 'Upload & Restore'
				}}
			</Button>
		</template>
	</Dialog>
</template>
<script>
import { Button } from 'frappe-ui';
import BackupFilesUploader from './BackupFilesUploader.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteDatabaseRestoreDialog',
	props: {
		site: {
			type: String,
			required: true,
		},
	},
	components: {
		BackupFilesUploader,
		Button,
	},
	data() {
		return {
			showRestoreDialog: true,
			selectedFiles: {
				database: null,
				public: null,
				private: null,
				config: null,
			},
			skipFailingPatches: false,
			errorMessageFromUploader: '',
			uploadingFiles: false,
		};
	},
	methods: {
		async startUploadFiles() {
			this.errorMessageFromUploader = '';
			this.uploadingFiles = true;
			const success = await this.$refs.backupFilesUploader.uploadFiles();
			if (!success) {
				this.uploadingFiles = false;
			}
			if (this.$refs.backupFilesUploader.isAllFilesUploaded()) {
				this.startRestore(this.selectedFiles);
			}
		},
		startRestore(files) {
			this.uploadingFiles = false;
			if (files) {
				this.selectedFiles = files;
			}
			this.$resources.restoreBackup.submit({
				name: this.site,
				files: this.selectedFiles,
				skip_failing_patches: this.skipFailingPatches,
			});
		},
		failureHandler(e) {
			if (e) return;
			this.uploadingFiles = false;
			this.errorMessageFromUploader =
				'Failed to upload files. Please try again.';
			this.showRestoreDialog = false;
			toast.error(this.errorMessageFromUploader);
		},
	},
	resources: {
		restoreBackup() {
			return {
				url: 'press.api.site.restore',
				onSuccess() {
					this.selectedFiles = {};
					this.$router.push({
						name: 'Site Jobs',
						params: { name: this.site },
					});
					this.showRestoreDialog = false;
					this.$toast.success('Restoration triggered successfully.');
				},
			};
		},
	},
	computed: {
		filesUploaded() {
			return this.selectedFiles.database;
		},
	},
};
</script>
