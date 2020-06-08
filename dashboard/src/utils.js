import { DateTime } from 'luxon';

let utils = {
	methods: {
		$plural(number, singular, plural) {
			if (number === 1) {
				return singular;
			}
			return plural;
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
		formatBytes(bytes, decimals = 2) {
			if (bytes === 0) return '0 Bytes';

			const k = 1024;
			const dm = decimals < 0 ? 0 : decimals;
			const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

			const i = Math.floor(Math.log(bytes) / Math.log(k));

			return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
		}
	}
};

export default function install(Vue) {
	Vue.mixin(utils);
}
