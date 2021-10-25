<template>
	<div>
		<label class="text-lg font-semibold">
			Restore an existing site
		</label>
		<p class="text-base text-gray-700">
			Restore an existing site from backup files or directly from site url.
		</p>
		<div class="grid grid-cols-2 gap-6 mt-4">
			<Button
				v-for="tab in [
					{ name: 'Upload Backups', key: 'backup' },
					{ name: 'Migrate from Site URL', key: 'siteUrl' }
				]"
				:key="tab.key"
				:type="restoreFrom === tab.key ? 'primary' : 'secondary'"
				@click="restoreFrom = tab.key"
			>
				{{ tab.name }}
			</Button>
		</div>
		<div v-if="restoreFrom === 'backup'">
			<div
				class="px-4 py-3 mt-6 text-sm text-gray-700 border border-gray-300 rounded-md"
			>
				<ol class="pl-4 list-decimal">
					<li>Login to your site.</li>
					<li>From the Download Backups page, download the latest backup.</li>
					<li>
						To get files backup, click on Download Files Backup. This will
						generate a new files backup and you will get an email.
					</li>
					<li>
						Download the files backup from the links in the email and upload the
						files here.
					</li>
				</ol>
			</div>
			<Alert class="w-full mt-5" v-if="manualMigration">
				Seems like your site is huge. Open a support ticket mentioning that you
				want to restore a backup and it's size and we'll take it from there.
			</Alert>
			<BackupFilesUploader
				class="mt-6"
				:backupFiles="selectedFiles"
				@update:backupFiles="files => $emit('update:selectedFiles', files)"
			/>
		</div>
		<div v-if="restoreFrom === 'siteUrl'">
			<div class="mt-6">
				<div
					class="px-4 py-3 text-sm text-gray-700 border border-gray-300 rounded-md"
				>
					<ol class="pl-4 list-decimal">
						<li>Login to your site.</li>
						<li>
							From the Download Backups page, click on Download Files Backup.
						</li>
						<li>
							This will generate a new files backup and you will get an email.
						</li>
						<li>After that, come back here and click on Get Backups.</li>
					</ol>
				</div>
				<Alert
					class="w-full mt-5"
					v-if="
						errorContains('Your site exceeds the limits for this operation')
					"
				>
					Seems like your site is huge. Open a support ticket mentioning that
					you want to restore a backup and it's size and we'll take it from
					there.
				</Alert>
				<Form
					class="mt-6"
					:fields="[
						{
							label: 'Site URL',
							fieldtype: 'Data',
							fieldname: 'url'
						},
						{
							label: 'Email',
							fieldtype: 'Data',
							fieldname: 'email'
						},
						{
							label: 'Password',
							fieldtype: 'Password',
							fieldname: 'password'
						}
					]"
					v-model="frappeSite"
				/>
				<div class="mt-2">
					<ErrorMessage
						:error="$resources.getBackupLinks.error"
						v-if="!$resources.getBackupLinks.data"
					/>
					<div
						class="text-base font-semibold text-green-500"
						v-if="$resources.getBackupLinks.data"
					>
						Found latest backups at {{ fetchedBackupFiles[0].timestamp }}
					</div>
					<div class="mt-2 space-y-1" v-if="$resources.getBackupLinks.data">
						<div v-for="file in fetchedBackupFiles" :key="file.remote_file">
							<div class="text-base font-medium text-gray-700">
								{{ file.file_name }}
							</div>
						</div>
					</div>
				</div>
				<Button
					v-if="!$resources.getBackupLinks.data"
					class="mt-2"
					@click="$resources.getBackupLinks.submit()"
					:loading="$resources.getBackupLinks.loading"
				>
					Get Backups
				</Button>
			</div>
		</div>

		<div class="mt-3" v-if="['backup', 'siteUrl'].includes(restoreFrom)">
			<!-- Skip Failing Checkbox -->
			<input
				id="skip-failing"
				type="checkbox"
				class="
				h-4
				w-4
				text-blue-600
				focus:ring-blue-500
				border-gray-300
				rounded
			"
				v-model="wantToSkipFailingPatches"
			/>
			<label for="skip-failing" class="ml-2 text-sm text-gray-900">
				Skip failing patches (if any patch fails)
			</label>
		</div>
	</div>
</template>
<script>
import FileUploader from '@/components/FileUploader.vue';
import Form from '@/components/Form.vue';
import BackupFilesUploader from '@/components/BackupFilesUploader.vue';
import { DateTime } from 'luxon';

export default {
	name: 'Restore',
	props: ['options', 'selectedFiles', 'manualMigration', 'skipFailingPatches'],
	components: {
		FileUploader,
		Form,
		BackupFilesUploader
	},
	data() {
		return {
			restoreFrom: null,
			files: [
				{
					icon: 'database',
					type: 'database',
					ext: 'application/x-gzip',
					title: 'Database Backup',
					file: null
				},
				{
					icon: 'file',
					type: 'public',
					ext: 'application/x-tar',
					title: 'Public Files',
					file: null
				},
				{
					icon: 'file-minus',
					type: 'private',
					ext: 'application/x-tar',
					title: 'Private Files',
					file: null
				}
			],
			uploadedFiles: {
				database: null,
				public: null,
				private: null
			},
			frappeSite: {
				url: '',
				email: '',
				password: ''
			},
			errorMessage: null,
			wantToSkipFailingPatches: false
		};
	},
	resources: {
		getBackupLinks() {
			let { url, email, password } = this.frappeSite;
			return {
				method: 'press.api.site.get_backup_links',
				params: {
					url,
					email,
					password
				},
				validate() {
					let { url, email, password } = this.frappeSite;
					if (!(url && email && password)) {
						return 'Please enter URL, Username and Password';
					}
				},
				onSuccess(remoteFiles) {
					let selectedFiles = {};
					for (let file of remoteFiles) {
						selectedFiles[file.type] = file.remote_file;
					}
					this.$emit('update:selectedFiles', selectedFiles);
				}
			};
		}
	},
	methods: {
		showAlert() {
			this.manualMigration = true;
		},
		errorContains(word) {
			return (
				this.$resources.getBackupLinks.error &&
				this.$resources.getBackupLinks.error.search(word) !== -1
			);
		}
	},
	computed: {
		fetchedBackupFiles() {
			if (!this.$resources.getBackupLinks.data) {
				return [];
			}
			return this.$resources.getBackupLinks.data.map(file => {
				// Convert "20200820_124804-erpnextcom-private-files.tar" to "20200820T124804"
				// so DateTime can parse it
				let timestamp_string = file.file_name
					.split('-')[0]
					.split('_')
					.join('T');

				let formatted = DateTime.fromISO(timestamp_string).toLocaleString(
					DateTime.DATETIME_FULL
				);

				return {
					...file,
					timestamp: formatted
				};
			});
		}
	},
	watch: {
		wantToSkipFailingPatches(value) {
			this.$emit('update:skipFailingPatches', value);
		}
	}
};
</script>
