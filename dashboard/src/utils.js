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
		}
	}
};

export default function install(Vue) {
	Vue.mixin(utils);
}
