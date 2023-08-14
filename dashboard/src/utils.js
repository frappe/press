import { DateTime, Duration } from 'luxon';
import theme from '../tailwind.theme.json';

let utils = {
	methods: {
		$plural(number, singular, plural) {
			if (number === 1) {
				return singular;
			}
			return plural;
		},
		$getColorBasedOnString(i) {
			return ['blue', 'green', 'red', 'orange'][i];
		},
		$date(date, serverDatesTimezone = 'Asia/Kolkata') {
			// assuming all dates on the server are stored in our timezone

			let localZone = DateTime.local().zoneName;
			return DateTime.fromSQL(date, { zone: serverDatesTimezone }).setZone(
				localZone
			);
		},
		round(number, precision) {
			let multiplier = Math.pow(10, precision || 0);
			return Math.round(number * multiplier) / multiplier;
		},
		formatDate(value, type = 'DATETIME_FULL', isUTC = false) {
			let datetime = isUTC ? this.$date(value, 'UTC') : this.$date(value);
			let format = value;
			if (type === 'relative') {
				format = datetime.toRelative();
			} else {
				let formatOptions = DateTime[type];
				format = datetime.toLocaleString(formatOptions);
			}
			return format;
		},
		$formatDuration(value) {
			// Remove decimal seconds
			value = value.split('.')[0];

			// Add leading zero
			// 0:0:2 -> 00:00:02
			const formattedDuration = value
				.split(':')
				.map(x => x.padStart(2, '0'))
				.join(':');

			const dateTime = Duration.fromISOTime(formattedDuration).toObject();
			const hourString = dateTime.hours ? `${dateTime.hours}h` : '';
			const minuteString = dateTime.minutes ? `${dateTime.minutes}m` : '';
			const secondString = `${dateTime.seconds}s`;

			return `${hourString} ${minuteString} ${secondString}`;
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
		$formatCPUTime(duration) {
			return duration / 1000000;
		},
		$planTitle(plan) {
			let india = this.$account.team.country == 'India';
			let currency = india ? '₹' : '$';
			let price_field = india ? 'price_inr' : 'price_usd';
			let price =
				plan.block_monthly == 1 ? plan[price_field] * 12 : plan[price_field];
			return price > 0 ? `${currency}${price}` : plan.plan_title;
		},
		trialEndsInDaysText(date) {
			let diff = this.$date(date).diff(DateTime.local(), ['days']).toObject();

			let days = diff.days;
			if (days > 1) {
				return `in ${Math.floor(days)} days`;
			}
			return 'in a day';
		},
		$routeTo404PageIfNotFound(errorMessage) {
			if (errorMessage.indexOf('not found') >= 0) {
				this.$router.push({
					name: 'NotFound',
					// preserve current path and remove the first char to avoid the target URL starting with `//`
					params: { pathMatch: this.$route.path.substring(1).split('/') },
					// preserve existing query and hash if any
					query: this.$route.query,
					hash: this.$route.hash
				});
			}
		},
		$siteStatus(site) {
			let status = site.status;
			if (site.update_available && site.status == 'Active') {
				status = 'Update Available';
			}

			let usage = Math.max(
				site.current_cpu_usage,
				site.current_database_usage,
				site.current_disk_usage
			);
			if (usage && usage >= 80 && status == 'Active') {
				status = 'Attention Required';
			}
			if (site.trial_end_date) {
				status = 'Trial';
			}
			return status;
		}
	},
	computed: {
		$theme() {
			return theme;
		},
		$platform() {
			const ua = navigator.userAgent.toLowerCase();

			if (ua.indexOf('win') > -1) {
				return 'win';
			} else if (ua.indexOf('mac') > -1) {
				return 'mac';
			} else if (ua.indexOf('x11') > -1 || ua.indexOf('linux') > -1) {
				return 'linux';
			}
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

export async function trypromise(promise) {
	try {
		let data = await promise;
		return [null, data];
	} catch (error) {
		return [error, null];
	}
}

export function validateSubdomain(subdomain) {
	if (!subdomain) {
		return 'Subdomain cannot be empty';
	}
	if (subdomain.length < 5) {
		return 'Subdomain too short. Use 5 or more characters';
	}
	if (subdomain.length > 32) {
		return 'Subdomain too long. Use 32 or less characters';
	}
	if (!subdomain.match(/^[a-z0-9][a-z0-9-]*[a-z0-9]$/)) {
		return 'Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens';
	}
	return null;
}

export { utils };
export { default as dayjs } from './utils/dayjs';
