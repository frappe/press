<template>
	<div>
		<label class="text-lg font-semibold">
			Restore an existing site
		</label>
		<p class="text-base text-gray-700">
			Restore an existing site from backup files or directly from site url.
		</p>
		<div class="flex mt-4 space-x-8">
			<button
				v-for="tab in [
					{ name: 'Upload Backups', key: 'backup' },
					{ name: 'Migrate from Site URL', key: 'siteUrl' }
				]"
				:key="tab.key"
				class="block px-1 py-4 text-base font-medium leading-none truncate border-b focus:outline-none"
				:class="
					restoreFrom === tab.key
						? 'border-brand text-gray-900'
						: 'text-gray-600 hover:text-gray-900 border-transparent'
				"
				@click="restoreFrom = tab.key"
			>
				{{ tab.name }}
			</button>
		</div>
		<div v-if="restoreFrom === 'backup'">
			<div class="px-4 py-3 mt-6 text-sm text-gray-700 border border-gray-300 rounded-md">
				<ol class="pl-4 list-decimal">
					<li>Login to your ERPNext site.</li>
					<li>From the Download Backups page, download the latest backup.</li>
					<li>To get files backup, click on Download Files Backup. This will generate a new files backup and you will get an email.</li>
					<li>Download the files backup from the links in the email and upload the files here.</li>
				</ol>
			</div>
			<div class="grid grid-cols-3 gap-4 mt-6">
				<FileUploader
					v-for="file in files"
					:fileTypes="file.ext"
					:key="file.type"
					:type="file.type"
					:s3="true"
					@success="onFileUpload(file, $event)"
					:upload-args="{
						method: 'press.api.site.upload_backup',
						type: file.type
					}"
				>
					<template
						v-slot="{
							file: fileObj,
							uploading,
							progress,
							message,
							error,
							success,
							openFileSelector
						}"
					>
						<button
							class="w-full h-full px-4 py-6 border rounded-md focus:outline-none focus:shadow-outline hover:border-blue-400"
							:class="success ? 'bg-blue-50 border-blue-500' : ''"
							@click="openFileSelector()"
							:disabled="uploading"
						>
							<FeatherIcon
								:name="success ? 'check' : file.icon"
								class="inline-block w-5 h-5 text-gray-700"
							/>
							<div
								class="mt-3 text-base font-semibold leading-none text-gray-800"
							>
								{{ file.title }}
							</div>
							<div
								class="mt-2 text-xs leading-snug text-gray-700"
								v-if="fileObj"
							>
								{{ fileObj.name }}
							</div>
							<div class="text-base" v-if="progress && progress !== 100">
								{{ progress }} %
							</div>
							<div class="mt-2 text-sm text-red-600" v-if="error">
								{{ error }}
							</div>
							<div
								class="mt-2 text-xs text-gray-500"
								v-if="!(progress || error) || message"
							>
								{{ message || 'Click to upload' }}
							</div>
						</button>
					</template>
				</FileUploader>
			</div>
		</div>
		<div v-if="restoreFrom === 'siteUrl'">
			<div class="mt-6">
				<div class="px-4 py-3 text-sm text-gray-700 border border-gray-300 rounded-md">
					<ol class="pl-4 list-decimal">
						<li>Login to your ERPNext site.</li>
						<li>From the Download Backups page, click on Download Files Backup.</li>
						<li>This will generate a new files backup and you will get an email.</li>
						<li>After that, come back here and click on Get Backups.</li>
					</ol>
				</div>
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
					<ErrorMessage :error="$resources.getBackupLinks.error" v-if="!$resources.getBackupLinks.data" />
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
	</div>
</template>
<script>
import FileUploader from '@/components/FileUploader';
import Form from '@/components/Form';
import { DateTime } from 'luxon';

export default {
	name: 'Restore',
	props: ['options', 'selectedFiles'],
	components: {
		FileUploader,
		Form
	},
	data() {
		return {
			restoreFrom: 'backup',
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
			errorMessage: null
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
		onFileUpload(file, fileurl) {
			this.uploadedFiles[file.type] = fileurl;
			this.$emit('update:selectedFiles', this.uploadedFiles);
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
	}
};
</script>
