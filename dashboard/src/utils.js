import { DateTime } from 'luxon';
import theme from '../tailwind.theme.json';

let utils = {
	methods: {
		$plural(number, singular, plural) {
			if (number === 1) {
				return singular;
			}
			return plural;
		},
		$date(date) {
			// assuming all dates on the server are stored in our timezone
			let serverDatesTimezone = 'Asia/Kolkata';
			let localZone = DateTime.local().zoneName;
			return DateTime.fromSQL(date, { zone: serverDatesTimezone }).setZone(
				localZone
			);
		},
		round(number, precision) {
			let multiplier = Math.pow(10, precision || 0);
			return Math.round(number * multiplier) / multiplier;
		},
		formatDate(value, type = 'DATETIME_FULL') {
			let datetime = this.$date(value);
			let format = value;
			if (type === 'relative') {
				format = datetime.toRelative();
			} else {
				let formatOptions = DateTime[type];
				format = datetime.toLocaleString(formatOptions);
			}
			return format;
		},
		formatBytes(bytes, decimals = 2, current = 0) {
			if (bytes === 0) return '0 Bytes';

			const k = 1024;
			const dm = decimals < 0 ? 0 : decimals;
			const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
			const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

			return (
				parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) +
				' ' +
				sizes[i + current]
			);
		},
		$planTitle(plan) {
			let india = this.$account.team.country == 'India';
			let currency = india ? '₹' : '$';
			let price_field = india ? 'price_inr' : 'price_usd';
			let price = plan[price_field];
			return price > 0 ? `${currency}${price}` : plan.plan_title;
		}
	},
	computed: {
		$theme() {
			return theme;
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

export function isWasmSupported() {
	// Check if browser supports WASM
	// ref: https://stackoverflow.com/a/47880734/10309266
	return (() => {
		try {
			if (
				typeof WebAssembly === 'object' &&
				typeof WebAssembly.instantiate === 'function'
			) {
				const module = new WebAssembly.Module(
					Uint8Array.of(0x0, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00)
				);
				if (module instanceof WebAssembly.Module)
					return (
						new WebAssembly.Instance(module) instanceof WebAssembly.Instance
					);
			}
		} catch (e) {} // eslint-disable-line no-empty
		return false;
	})();
}
