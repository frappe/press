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

			// Check for upload size limits
			this.message = 'Checking File Limits';
			if (
				this.file.type === 'application/x-gzip' &&
				this.file.size > 524 * 1000 * 1000
			) {
				this.error = 'Max File Size Limit for Database file is 500M';
				this.message = '';
				return;
			}

			// Check for validity of files
			this.message = 'Validating File';
			const validationMessage = await this.validateFile();
			const validationName = await this.validateFileName();
			this.message = '';

			// Try uploading the files
			if (validationMessage === true) {
				this.uploadFile(this.file);
			} else if (validationName && validationMessage !== false) {
				this.uploadFile(this.file);
			} else {
				const title = this.type[0].toUpperCase() + this.type.slice(1);
				const errorTitle =
					validationMessage?.length > 24
						? 'Validation Error'
						: validationMessage;
				this.error = validationMessage ? errorTitle : `Invalid ${title} File`;
				if (validationMessage) {
					this.message = 'Skipping Validation...';
					console.error(validationMessage);
					setTimeout(() => {
						this.message = '';
						this.uploadFile(this.file);
					}, 3000);
				}
			}
		},
		validateFileName() {
			return new Promise((resolve, reject) => {
				const name = this.file.name;
				const suffix = `${this.type ? 'private' : ''}-files.tar`;
				const result = name.indexOf(suffix, name.length - suffix.length) !== -1;
				resolve(result);
			});
		},
		validateFile() {
			if (this.file.type !== 'application/x-tar') {
				console.error('File not validated!');
				return Promise.resolve(true);
			}
			return new Promise((resolve, reject) => {
				let timeout;
				if (this.file.size < 200 * 1000 * 1000) {
					timeout = 30 * 1000;
				} else {
					timeout = 60 * 1000;
				}
				let upload_type = this.type;
				let reader = new FileReader();
				reader.readAsArrayBuffer(this.file);
				reader.onload = function() {
					setTimeout(() => {
						_unarchiver?.stop();
						resolve('Validation Timed Out');
					}, timeout);

					const FileArrayBuffer = reader.result;
					let _unarchiver = new Untarrer(
						FileArrayBuffer,
						'/assets/press/node_modules/@codedread/bitjs/'
					);

					function readCompression(e) {
						if (e.currentFileNumber == 1) {
							const path = e.currentFilename.split('/');
							const type = path.indexOf(upload_type) == 2;
							const files = path.indexOf('files') == 3;
							_unarchiver.stop();
							if (type && files) {
								resolve(true);
							}
							resolve(false);
						}
					}

					_unarchiver.addEventListener('progress', readCompression);
					_unarchiver.start();
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
