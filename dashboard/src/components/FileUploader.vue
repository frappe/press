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
import { Archive } from 'libarchive.js/main.js';
import { isWasmSupported } from '@/utils';

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

			if (this.file.type === 'application/x-gzip') {
				let error = await this.validateDatabaseFile();
				if (error) {
					this.error = error;
					return;
				}
			}
			this.uploadFile(this.file);
		},
		async validateDatabaseFile() {
			// Check for upload size limits
			this.message = 'Checking File Limits';
			if (
				this.file.type === 'application/x-gzip' &&
				this.file.size > 524 * 1000 * 1000
			) {
				this.error = 'Max File Size Limit for Database file is 500M';
				this.message = '';
				this.$emit('failure', 'showAlert');
				return;
			}

			// Check for validity of files
			let validationMessage;
			if (isWasmSupported) {
				this.message = 'Validating File';
				validationMessage = await this.validateFile();
				this.message = '';
			} else {
				validationMessage = 'WASM not supported on this browser';
			}

			if (!validationMessage) {
				return null;
			}

			if (validationMessage) {
				this.message = 'Skipping Validation...';
				console.error(validationMessage);

				let after3secs = new Promise(resolve => {
					setTimeout(() => {
						this.message = '';
						resolve(null);
					}, 3000);
				});
				return after3secs;
			}
		},
		validateBackupFileContents() {
			return new Promise(resolve => {
				let timeout;
				if (this.file.size < 200 * 1000 * 1000) {
					timeout = 15 * 1000;
				} else {
					timeout = 30 * 1000;
				}
				let upload_type = this.type;

				setTimeout(() => {
					resolve('Validation Timed Out');
				}, timeout);

				Archive.init({
					workerUrl:
						'/assets/press/node_modules/libarchive.js/dist/worker-bundle.js'
				});
				Archive.open(this.file)
					.then(archive => {
						archive
							.getFilesArray()
							.then(files => {
								if (files.length > 0) {
									const path = files[0].path.split('/');
									const type = path.indexOf(upload_type) === 2;
									const compressed_files = path.indexOf('files') === 3;
									resolve(type && compressed_files);
								}
							})
							.catch(err => {
								resolve(`An error occurred while reading Files Array: ${err}`);
							});
					})
					.catch(err => {
						resolve(`An error occurred while reading compressed file: ${err}`);
					});
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
