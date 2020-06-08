<template>
	<div>
		<Section
			title="Restore"
			description="Restore your database using a previous backup."
		>
			<SectionCard>
				<div class="py-2 space-y-4">
					<div class="flex grid grid-cols-3 gap-4 px-6">
						<FileUploader
							v-for="file in files"
							:key="file.type"
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
									<div class="mt-2 text-xs text-gray-500" v-if="!progress">
										Click to upload
									</div>
								</button>
							</template>
						</FileUploader>
					</div>
					<div class="px-6">
						<Button
							type="primary"
							:disabled="!filesUploaded"
							:loading="$resources.restoreBackup.loading"
							@click="$resources.restoreBackup.submit()"
						>
							Restore
						</Button>
					</div>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
import FileUploader from '@/components/FileUploader';

export default {
	name: 'SiteDatabase',
	components: {
		FileUploader
	},
	props: ['site'],
	resources: {
		restoreBackup() {
			return {
				method: 'press.api.site.restore',
				params: {
					name: this.site.name,
					files: this.selectedFiles
				},
				onSuccess() {
					this.selectedFiles = {};
					this.$router.push(`/sites/${this.site.name}/installing`);
					setTimeout(() => {
						window.location.reload();
					}, 1000);
				}
			};
		}
	},
	data() {
		return {
			selectedFiles: {
				database: null,
				public: null,
				private: null
			},
			files: [
				{
					icon: 'database',
					type: 'database',
					title: 'Database Backup',
					file: null
				},
				{
					icon: 'file',
					type: 'public',
					title: 'Public Files',
					file: null
				},
				{
					icon: 'file-minus',
					type: 'private',
					title: 'Private Files',
					file: null
				}
			]
		};
	},
	methods: {
		onFileUpload(file, fileurl) {
			this.selectedFiles[file.type] = fileurl;
		}
	},
	computed: {
		filesUploaded() {
			return (
				this.selectedFiles.database &&
				this.selectedFiles.public &&
				this.selectedFiles.private
			);
		}
	}
};
</script>
