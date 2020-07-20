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
				message,
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
import { Untarrer } from '@codedread/bitjs/archive/archive';

export default {
	name: 'FileUploader',
	props: ['fileTypes', 'uploadArgs', 's3', 'type'],
	data() {
		return {
			uploader: null,
			uploading: false,
			uploaded: 0,
			error: null,
			message: '',
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
		async onFileAdd(e) {
			this.error = null;
			this.file = e.target.files[0];
			this.message = 'Validating File';
			const validationMessage = await this.validateFile();
			this.message = '';

			if (validationMessage === true) {
				delete window._unarchiver;
				this.uploadFile(this.file);
			} else {
				const title = this.type[0].toUpperCase() + this.type.slice(1);
				const errorTitle =
					validationMessage?.length > 10
						? 'Validation Error'
						: validationMessage;
				console.error(validationMessage);
				this.error = validationMessage ? errorTitle : `Invalid ${title} File`;
				if (validationMessage) {
					this.message = 'Skipping Validation...';
					setTimeout(() => {
						this.message = '';
						this.uploadFile(this.file);
					}, 3000);
				}
			}
		},
		validateFile() {
			if (this.file.type !== 'application/x-tar') {
				console.error('File not validated!');
				return Promise.resolve(true);
			}
			return new Promise((resolve, reject) => {
				setTimeout(() => {
					window._unarchiver?.stop();
					resolve('Validation Timed Out');
				}, 100000);
				let upload_type = this.type;
				let reader = new FileReader();
				reader.readAsArrayBuffer(this.file);
				reader.onload = function() {
					const FileArrayBuffer = reader.result;
					window._unarchiver = new Untarrer(
						FileArrayBuffer,
						'/assets/press/node_modules/@codedread/bitjs/'
					);

					function readCompression(e) {
						if (e.currentFileNumber == 1) {
							const path = e.currentFilename.split('/');
							const type = path.indexOf(upload_type) == 2;
							const files = path.indexOf('files') == 3;
							window._unarchiver.stop();
							if (type && files) {
								resolve(true);
							}
							resolve(false);
						}
					}

					window._unarchiver.addEventListener('progress', readCompression);
					window._unarchiver.start();
				};
				reader.onerror = function() {
					resolve(reader.error.toString());
				};
			});
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
