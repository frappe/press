import dayjs from '../utils/dayjs';

export function formatBytes(bytes, decimals = 2, current = 0) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

	return (
		parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i + current]
	);
}

export function formatDuration(value) {
	if (!value) return;

	let [hours, minutes, seconds] = value.split(':');
	[hours, minutes, seconds] = [
		parseInt(hours),
		parseInt(minutes),
		parseInt(seconds)
	];

	let format = '';
	if (hours > 0) {
		format = 'H[h] m[m] s[s]';
	} else if (minutes > 0) {
		format = 'm[m] s[s]';
	} else {
		format = 's[s]';
	}
	return dayjs.duration({ hours, minutes, seconds }).format(format);
}

export function formatDateTime(value) {
	return dayjs(value).format('DD/MM/YYYY HH:mm:ss');
}
