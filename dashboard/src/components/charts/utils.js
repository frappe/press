function formatBytes(bytes, decimals = 2, current = 0) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

	return (
		parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i + current]
	);
}

function getUnit(value, seriesName) {
	if (seriesName === 'bytes') return formatBytes(value);
	else return `${+value.toFixed(2)} ${seriesName}`;
}

export { formatBytes, getUnit };
