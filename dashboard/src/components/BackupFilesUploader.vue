<template>
	<div class="grid grid-cols-3 gap-4">
		<FileUploader
			v-for="file in files"
			:fileTypes="file.ext"
			:key="file.type"
			:type="file.type"
			@success="onFileUpload(file, $event)"
			:upload-args="{
				method: 'press.api.site.upload_backup',
				type: file.type
			}"
			:s3="true"
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
					class="w-full h-full px-4 py-6 border border-transparent rounded-md bg-gray-50 focus:outline-none focus:shadow-outline hover:border-blue-300 hover:bg-white"
					:class="success ? 'bg-blue-50 border-blue-500' : ''"
					@click="openFileSelector()"
					:disabled="uploading"
				>
					<div class="inline-block" v-html="file.icon"></div>
					<div class="mt-3 text-sm font-medium leading-none text-gray-800">
						{{ file.title }}
					</div>
					<div class="mt-2 text-xs leading-snug text-gray-700" v-if="fileObj">
						{{ fileObj.name }}
					</div>
					<div class="text-base" v-if="progress && progress !== 100">
						{{ progress }} %
					</div>
					<div class="mt-2 text-sm text-red-600" v-if="error">
						{{ error }}
					</div>
					<div
						class="mt-1 text-xs text-gray-600"
						v-if="!(progress || error) || message"
					>
						{{ message || 'Click to upload' }}
					</div>
				</button>
			</template>
		</FileUploader>
	</div>
</template>
<script>
import FileUploader from './FileUploader.vue';

export default {
	name: 'BackupFilesUploader',
	components: { FileUploader },
	props: ['backupFiles'],
	data() {
		return {
			files: [
				{
					icon:
						'<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5.33325 9.33333V22.6667C5.33325 25.6133 10.1093 28 15.9999 28C21.8906 28 26.6666 25.6133 26.6666 22.6667V9.33333M5.33325 9.33333C5.33325 12.28 10.1093 14.6667 15.9999 14.6667C21.8906 14.6667 26.6666 12.28 26.6666 9.33333M5.33325 9.33333C5.33325 6.38667 10.1093 4 15.9999 4C21.8906 4 26.6666 6.38667 26.6666 9.33333M26.6666 16C26.6666 18.9467 21.8906 21.3333 15.9999 21.3333C10.1093 21.3333 5.33325 18.9467 5.33325 16" stroke="#1F272E" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
					type: 'database',
					ext: 'application/x-gzip',
					title: 'Database Backup',
					file: null
				},
				{
					icon:
						'<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9.39111 6.3913H26.3476V22.2174C26.3476 25.9478 23.2955 29 19.565 29H9.39111V6.3913Z" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M13.9131 13.1739H21.8261" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M13.9131 17.6957H21.8261" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M13.9131 22.2173H19.8479" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M22.9565 6.3913V3H6V25.6087H9.3913" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/></svg>',
					type: 'public',
					ext: 'application/x-tar',
					title: 'Public Files',
					file: null
				},
				{
					icon:
						'<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.39111 6.3913H25.3476V22.2174C25.3476 25.9478 22.2955 29 18.565 29H8.39111V6.3913Z" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/><path d="M21.9565 6.3913V3H5V25.6087H8.3913" stroke="#1F272E" stroke-width="1.5" stroke-miterlimit="10"/></svg>',
					type: 'private',
					ext: 'application/x-tar',
					title: 'Private Files',
					file: null
				}
			]
		};
	},
	methods: {
		onFileUpload(file, fileurl) {
			let backupFiles = Object.assign({}, this.backupFiles);
			backupFiles[file.type] = fileurl;
			this.$emit('update:backupFiles', backupFiles);
		}
	}
};
</script>
