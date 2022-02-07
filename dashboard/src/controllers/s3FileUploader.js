import call from './call';

export default class S3FileUploader {
	constructor() {
		this.listeners = {};
	}

	on(event, handler) {
		this.listeners[event] = this.listeners[event] || [];
		this.listeners[event].push(handler);
	}

	trigger(event, data) {
		let handlers = this.listeners[event] || [];
		handlers.forEach(handler => {
			handler.call(this, data);
		});
	}

	upload(file, options) {
		return new Promise(async (resolve, reject) => {
			async function getUploadLink() {
				try {
					let response = await fetch(
						`/api/method/press.api.site.get_upload_link?file=${file.name}`
					);
					let data = await response.json();
					return data.message;
				} catch (e) {
					reject(e);
				}
			}
			const upload_link = await getUploadLink();
			const file_path = upload_link?.fields?.key;

			if (!file_path) {
				return;
			}

			let xhr = new XMLHttpRequest();
			xhr.upload.addEventListener('loadstart', () => {
				this.trigger('start');
			});
			xhr.upload.addEventListener('progress', e => {
				if (e.lengthComputable) {
					this.trigger('progress', {
						uploaded: e.loaded,
						total: e.total
					});
				}
			});
			xhr.upload.addEventListener('load', () => {
				this.trigger('finish');
			});
			xhr.addEventListener('error', () => {
				this.trigger('error');
				reject();
			});
			xhr.onreadystatechange = () => {
				if (xhr.readyState == XMLHttpRequest.DONE) {
					let error;
					if (xhr.status === 200 || xhr.status === 204) {
						let r = null;
						try {
							r = JSON.parse(xhr.responseText);
						} catch (e) {
							r = xhr.responseText;
						}
						let out =
							r.message ||
							call('press.api.site.uploaded_backup_info', {
								file: file.name,
								path: file_path,
								type: file.type,
								size: file.size
							});
						resolve(out || upload_link.fields.key);
					} else {
						// response from aws is in xml
						let xmlDoc = new DOMParser().parseFromString(
							xhr.responseText,
							'text/xml'
						);
						let code =
							xmlDoc.getElementsByTagName('Code')[0].childNodes[0].nodeValue;
						let message =
							xmlDoc.getElementsByTagName('Message')[0].childNodes[0].nodeValue;
						console.error(`${code}: ${message}`);
						error = xhr.responseText;
					}
					if (error && error.exc) {
						console.error(JSON.parse(error.exc)[0]);
					}
					reject(error);
				}
			};

			xhr.open('POST', upload_link.url, true);
			xhr.setRequestHeader('Accept', 'application/json');

			let form_data = new FormData();
			for (let key in upload_link.fields) {
				if (upload_link.fields.hasOwnProperty(key)) {
					form_data.append(key, upload_link.fields[key]);
				}
			}
			if (file) {
				form_data.append('file', file, file.name);
			}

			xhr.send(form_data);
		});
	}
}
