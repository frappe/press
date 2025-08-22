<template>
	<div>
		<div class="mt-2 space-y-2">
			<FileUploader
				v-for="file in files"
				:fileTypes="file.ext"
				:ref="file.type"
				:key="file.type"
				:type="file.type"
				@success="onFileUpload(file, $event)"
				@failure="(e) => onFileUploadFailure(e)"
				@setFile="file.file = $event"
				:fileValidator="(f) => backupFileChecker(f, file.type)"
				:s3="true"
				:disableAutoUpload="true"
			>
				<template
					v-slot="{
						file: fileObj,
						uploading,
						uploaded,
						progress,
						error,
						success,
						openFileSelector,
					}"
				>
					<ListItem
						class="border-b"
						:title="fileObj ? fileObj.name : file.title"
					>
						<template #subtitle>
							<span
								class="text-base"
								:class="error ? 'text-red-500' : 'text-gray-600'"
							>
								{{
									uploading
										? `Uploading ${progress}%`
										: success
											? formatBytes(fileObj.size)
											: error
												? null
												: file.description
								}}
								<span v-if="error" v-html="error" />
							</span>
						</template>
						<template #actions>
							<Button
								:loading="uploading"
								loadingText="Uploading"
								@click="openFileSelector()"
								:disabled="uploading || success || disableUploadButton"
								v-if="!success"
							>
								Upload
							</Button>
							<GreenCheckIcon class="w-5" v-if="success" />
						</template>
					</ListItem>
				</template>
			</FileUploader>
		</div>
	</div>
</template>
<script>
import FileUploader from './FileUploader.vue';
import { createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'BackupFilesUploader',
	components: { FileUploader },
	emits: ['update:backupFiles', 'uploadComplete'],
	props: [
		'backupFiles',
		'site',
		'onError',
		'disableUploadButton',
		'abortUpload',
	],
	data() {
		return {
			files: [
				{
					icon: '<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5.33325 9.33333V22.6667C5.33325 25.6133 10.1093 28 15.9999 28C21.8906 28 26.6666 25.6133 26.6666 22.6667V9.33333M5.33325 9.33333C5.33325 12.28 10.1093 14.6667 15.9999 14.6667C21.8906 14.6667 26.6666 12.28 26.6666 9.33333M5.33325 9.33333C5.33325 6.38667 10.1093 4 15.9999 4C21.8906 4 26.6666 6.38667 26.6666 9.33333M26.6666 16C26.6666 18.9467 21.8906 21.3333 15.9999 21.3333C10.1093 21.3333 5.33325 18.9467 5.33325 16" stroke="#1F272E" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
					type: 'database',
					ext: '.sql,.sql.gz,application/sql,application/x-gzip,application/gzip',
					title: 'Database Backup',
					description:
						'Upload the database backup file. Usually file name ends in .sql.gz or .sql',
					file: null,
				},
				{
					icon: '<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9.39111 6.3913H26.3476V22.2174C26.3476 25.9478 23.2955 29 19.565 29H9.39111V6.3913Z" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M13.9131 13.1739H21.8261" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M13.9131 17.6957H21.8261" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M13.9131 22.2173H19.8479" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M22.9565 6.3913V3H6V25.6087H9.3913" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/></svg>',
					type: 'public',
					ext: 'application/x-tar',
					title: 'Public Files',
					description:
						'Upload the public files backup. Usually file name ends in -files.tar',
					file: null,
				},
				{
					icon: '<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.39111 6.3913H25.3476V22.2174C25.3476 25.9478 22.2955 29 18.565 29H8.39111V6.3913Z" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M21.9565 6.3913V3H5V25.6087H8.3913" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/></svg>',
					type: 'private',
					ext: 'application/x-tar',
					title: 'Private Files',
					description:
						'Upload the private files backup. Usually file name ends in -private-files.tar',
					file: null,
				},
				{
					icon: '<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.39111 6.3913H25.3476V22.2174C25.3476 25.9478 22.2955 29 18.565 29H8.39111V6.3913Z" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M21.9565 6.3913V3H5V25.6087H8.3913" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/></svg>',
					type: 'config',
					ext: 'application/json',
					title: 'Site Config (required if backup is encrypted)',
					description:
						'Upload the site config file. Usually file name ends in -site_config_backup.json',
					file: null,
				},
			],
			fileSize: {
				database: 0,
				public: 0,
				private: 0,
				config: 0,
			},
		};
	},
	methods: {
		onFileUpload(file, data) {
			let backupFiles = Object.assign({}, this.backupFiles);
			backupFiles[file.type] = data;
			this.$emit('update:backupFiles', backupFiles);
			if (this.isAllFilesUploaded(backupFiles)) {
				this.$emit('uploadComplete', backupFiles);
			}
		},
		onFileUploadFailure(e) {
			this.$emit('abortUpload', e);
		},
		async backupFileChecker(file, type) {
			this.fileSize[type] = file?.size ?? 0;

			if (file.size > 5 * 1024 * 1024 * 1024) {
				throw new Error(
					'File size exceeds the limit of 5 GiB. Please try the <a href="https://docs.frappe.io/cloud/sites/migrate-an-existing-site#migrate-using-python-script" class=underline>migrate</a> script.',
				);
			}

			if (type === 'database') {
				// valid strings are "database.sql.gz", "database.sql", "database.sql (1).gz", "database.sql (2).gz"
				if (!/\.sql( \(\d\))?\.gz$|\.sql$/.test(file.name)) {
					throw new Error(
						'Database backup file should end with the name "database.sql.gz" or "database.sql"',
					);
				}
				if (
					![
						'application/x-gzip',
						'application/gzip',
						'application/sql',
					].includes(file.type)
				) {
					throw new Error('Invalid database backup file');
				}
			}
			if (['public', 'private'].includes(type)) {
				if (file.type != 'application/x-tar') {
					throw new Error(`Invalid ${type} files backup file`);
				}
			}
			if (type === 'config') {
				if (file.type != 'application/json') {
					throw new Error(`Invalid ${type} files backup file`);
				}
			}
		},
		async checkServerDiskSize() {
			if (!this.site) {
				// If site is not provided, we cannot check the disk size
				return true;
			}
			let post = createResource({
				url: 'press.api.site.validate_restoration_space_requirements',
				method: 'POST',
			});
			return post.fetch({
				name: this.site,
				db_file_size: this.fileSize.database || 0,
				public_file_size: this.fileSize.public || 0,
				private_file_size: this.fileSize.private || 0,
			});
		},
		isAllFilesUploaded(backupFiles) {
			return (
				Object.values(backupFiles || this.backupFiles).filter((e) => e)
					.length === this.files.filter((e) => e.file).length
			);
		},
		async uploadFiles() {
			let response = await this.checkServerDiskSize();
			if (!response.allowed_to_upload) {
				let errorMessage = '';
				if (response.is_insufficient_space_on_app_server) {
					let requiredGB = Math.round(
						(response.required_space_on_app_server -
							response.free_space_on_app_server) /
							(1024 * 1024 * 1024),
						2,
					);
					errorMessage += `Insufficient space on app server. Please add ${requiredGB} GB more storage.`;
				}
				if (response.is_insufficient_space_on_db_server) {
					let requiredGB = Math.round(
						(response.required_space_on_db_server -
							response.free_space_on_db_server) /
							(1024 * 1024 * 1024),
						2,
					);
					errorMessage += ` Insufficient space on database server. Please add ${requiredGB} GB more storage.`;
				}
				if (!errorMessage) {
					errorMessage = 'Failed to upload files. Please try again later.';
				}
				if (this.onError) {
					this.onError(errorMessage);
				}
				toast.error(errorMessage);
				return false;
			}

			if (this.$refs.database) {
				this.$refs.database[0].uploadFile();
			}
			if (this.$refs.public) {
				this.$refs.public[0].uploadFile();
			}
			if (this.$refs.private) {
				this.$refs.private[0].uploadFile();
			}
			if (this.$refs.config) {
				this.$refs.config[0].uploadFile();
			}

			return true;
		},
	},
};
</script>
