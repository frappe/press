<template>
	<div>
		<input
			ref="input"
			type="file"
			:accept="fileTypes"
			class="hidden"
			@change="onFileAdd"
		/>
		<slot
			v-bind="{
				file,
				uploading,
				progress,
				uploaded,
				error,
				total,
				success,
				openFileSelector
			}"
		/>
	</div>
</template>

<script>
import FileUploader from '@/controllers/fileUploader';
import S3FileUploader from '@/controllers/s3FileUploader';

export default {
	name: 'FileUploader',
	props: ['fileTypes', 'uploadArgs', 's3'],
	data() {
		return {
			uploader: null,
			uploading: false,
			uploaded: 0,
			error: null,
			total: 0,
			file: null,
			finishedUploading: false
		};
	},
	computed: {
		progress() {
			return Math.floor((this.uploaded / this.total) * 100);
		},
		success() {
			return this.finishedUploading && !this.error;
		}
	},
	methods: {
		openFileSelector() {
			this.$refs['input'].click();
		},
		onFileAdd(e) {
			this.file = e.target.files[0];
			this.uploadFile(this.file);
		},
		async uploadFile(file) {
			this.error = null;
			this.uploaded = 0;
			this.total = 0;

			this.uploader = this.s3 ? new S3FileUploader() : new FileUploader();
			this.uploader.on('start', () => {
				this.uploading = true;
			});
			this.uploader.on('progress', data => {
				this.uploaded = data.uploaded;
				this.total = data.total;
			});
			this.uploader.on('error', () => {
				this.uploading = false;
				this.error = 'Error Uploading File';
			});
			this.uploader.on('finish', () => {
				this.uploading = false;
				this.finishedUploading = true;
			});
			this.uploader
				.upload(file, this.uploadArgs || {})
				.then(data => {
					this.$emit('success', data);
				})
				.catch(error => {
					this.uploading = false;
					let errorMessage = 'Error Uploading File';
					if (error._server_messages) {
						errorMessage = JSON.parse(JSON.parse(error._server_messages)[0])
							.message;
					} else if (error.exc) {
						errorMessage = JSON.parse(error.exc)[0]
							.split('\n')
							.slice(-2, -1)[0];
					}
					this.error = errorMessage;
					this.$emit('failure', error);
				});
		}
	}
};
</script>
