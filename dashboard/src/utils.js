import { DateTime } from 'luxon';

let utils = {
	methods: {
		$plural(number, singular, plural) {
			if (number === 1) {
				return singular;
			}
			return plural;
		},
		$date(date) {
			return DateTime.fromSQL(date);
		},
		formatDate(value, type = 'full') {
			let datetime = DateTime.fromSQL(value);
			let format = value;
			if (type === 'relative') {
				format = datetime.toRelative();
			} else if (type === 'full') {
				format = datetime.toLocaleString(DateTime.DATETIME_FULL);
			}
			return format;
		},
		formatBytes(bytes, decimals = 2, current = 0) {
			if (bytes === 0) return '0 Bytes';

			const k = 1024;
			const dm = decimals < 0 ? 0 : decimals;
			const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
			const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

			return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i + current];
		}
	}
};

export function validateGST(gst) {
	// https://github.com/raysk4ever/raysk-vali/blob/master/validate.js#L51
	const gstReg = new RegExp(
		/\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}/
	);
	return gstReg.test(gst);
}

export default function install(Vue) {
	Vue.mixin(utils);
}
