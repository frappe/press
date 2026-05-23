import dayjs, { dayjsLocal } from '../utils/dayjs';
import { getTeam } from '../data/team';
import { format } from 'sql-formatter';
import { getConfig } from 'frappe-ui';

export function bytes(bytes, decimals = 2, current = 0) {
	if (bytes === 0) return '0 Octets';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;
	const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	let i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
	if (i < 0) i++;

	return (
		parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i + current]
	);
}

// Chart utility function for getting formatted units
export function getUnit(value, seriesName) {
	if (seriesName === 'bytes') return bytes(value);
	else return `${+value.toFixed(2)} ${seriesName}`;
}

export function duration(value) {
	if (!value) return;

	let [hours, minutes, seconds] = value.split(':');
	[hours, minutes, seconds] = [
		parseInt(hours),
		parseInt(minutes),
		parseInt(seconds),
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

export const secsToDuration = (seconds) => {
	if (seconds == null) return '';
	seconds = Math.floor(seconds);

	if (seconds <= 0) return '0s';

	const hours = Math.floor(seconds / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	const secs = seconds % 60;

	let parts = [];

	if (hours) parts.push(`${hours}h`);
	if (minutes) parts.push(`${minutes}m`);
	if (secs) parts.push(`${secs}s`);

	return parts.join(' ');
}

export function plural(number, singular, plural) {
	if (typeof number === 'string') {
		number = parseInt(number);
	}
	if (number === 1) {
		return singular;
	}
	return plural;
}

export function planTitleHourly(plan) {
	if (plan === undefined) return;
	const priceField = 'price_dzd';
	const price =
		plan?.block_monthly == 1 ? plan[priceField] * 12 : plan[priceField];

	return price > 0 ? `${userCurrency(pricePerHour(price))}` : plan.plan_title;
}

export function planTitle(plan) {
	if (plan === undefined) return;
	const priceField = 'price_dzd';
	const price =
		plan?.block_monthly == 1 ? plan[priceField] * 12 : plan[priceField];
	return price > 0 ? `${userCurrency(price, 0)}` : plan.plan_title;
}

export function userCurrency(value, fractions = 2) {
	const $team = getTeam();
	if (!$team.doc?.currency) return value;
	return currency(value, $team.doc?.currency, fractions);
}

export function currency(value, curr, fractions = 2) {
	if (curr === 'DZD') {
		return new Intl.NumberFormat('fr-DZ', {
			style: 'currency',
			currency: 'DZD',
			maximumFractionDigits: fractions,
		}).format(value);
	}
	return new Intl.NumberFormat('fr-FR', {
		style: 'currency',
		currency: curr || 'DZD',
		maximumFractionDigits: fractions,
	}).format(value);
}

export function numberK(number) {
	if (number < 1000) {
		return number;
	} else {
		let value = Math.round(number / 1000, 1);

		// To handle cases like 8.0, 9.0 etc.
		if (value == number / 1000) {
			value = parseInt(value);
		}
		// To handle cases like 8999 -> 9k and not 9.0k
		else if (value - 1 == number / 1000) {
			value = parseInt(value);
		}

		return `${value}k`;
	}
}

export function pricePerHour(price) {
	let daysInThisMonth = dayjs().daysInMonth();
	return price / daysInThisMonth / 24;
}

export function pricePerDay(price) {
	let daysInThisMonth = dayjs().daysInMonth();
	return price / daysInThisMonth;
}

export function utcDate(dateTimeString, format = 'LLLL') {
	if (!dateTimeString) return;
	return dayjs.utc(dateTimeString).local().format(format);
}

export function date(dateTimeString, format = 'LLLL') {
	if (!dateTimeString) return;
	return dayjsLocal(dateTimeString).format(format);
}

export function commaSeparator(arr, separator) {
	let joinedString = arr.slice(0, -1).join(', ');

	if (arr.length > 1) {
		joinedString += ` ${separator} ${arr[arr.length - 1]}`;
	} else {
		joinedString += arr[0];
	}

	return joinedString;
}

export function commaAnd(arr) {
	return commaSeparator(arr, 'et');
}

export function formatSQL(query) {
	try {
		return format(query, {
			language: 'mariadb',
			tabWidth: 2,
			keywordCase: 'upper',
		});
	} catch (_) {
		return query;
	}
}

export function formatSeconds(seconds) {
	if (seconds === 0) return '0s';
	if (seconds <= 60) return `${seconds}s`;

	const hours = Math.floor(seconds / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	const remainingSeconds = seconds % 60;

	let result = [];

	if (hours > 0) {
		result.push(`${hours}h`);
	}

	if (minutes > 0) {
		result.push(`${minutes}m`);
	}

	if (remainingSeconds > 0) {
		result.push(`${remainingSeconds}s`);
	}

	return result.join(' ');
}

export function formatCommaSeperatedNumber(number) {
	let numStr = number.toString();

	let lastThree = numStr.slice(-3);
	let remaining = numStr.slice(0, -3);

	let parts = [];
	while (remaining.length > 2) {
		parts.push(remaining.slice(-2));
		remaining = remaining.slice(0, -2);
	}

	if (remaining) {
		parts.push(remaining);
	}

	let result = parts.reverse().join(',') + ',' + lastThree;
	// truncate , at start or end
	result = result.replace(/^,/, '');
	result = result.replace(/,$/, '');
	return result;
}

export function formatMilliseconds(ms) {
	if (ms < 100) {
		return `${ms.toFixed(3).replace(/\.?0+$/, '')}ms`; // Keep milliseconds if less than 100 and remove unnecessary zeros
	} else if (ms < 60000) {
		// Less than 1 minute, convert to seconds
		let seconds = ms / 1000;
		return `${seconds.toFixed(1).replace(/\.?0+$/, '')}s`;
	} else {
		// Convert to minutes
		let minutes = ms / 60000;
		return `${minutes.toFixed(1).replace(/\.?0+$/, '')}m`;
	}
}

export function formatValue(value, type) {
	switch (type) {
		case 'bytes':
			return bytes(value);
		case 'date':
			return date(value);
		case 'duration':
			return duration(value);
		case 'durationSeconds':
			return formatSeconds(value);
		case 'durationMilliseconds':
			return formatMilliseconds(value);
		case 'commaSeperatedNumber':
			return formatCommaSeperatedNumber(value);
		case 'numberK':
			return numberK(value);
		case 'pricePerDay':
			return pricePerDay(value);
		case 'pricePerHour':
			return pricePerHour(value);
		case 'sql':
			return formatSQL(value);
		default:
			return value;
	}
}

export function startCase(str) {
	return str.charAt(0).toUpperCase() + str.slice(1);
}

export function timeAgo(date) {
	return prettyDate(date);
}

function getBrowserTimezone() {
	return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export function prettyDate(date, mini = false) {
	if (!date) return '';

	let systemTimezone = getConfig('systemTimezone');
	let localTimezone = getConfig('localTimezone') || getBrowserTimezone();

	if (typeof date == 'string') {
		date = dayjsLocal(date);
	}

	let nowDatetime = dayjs().tz(localTimezone || systemTimezone);
	let diff = nowDatetime.diff(date, 'seconds');

	let dayDiff = diff / 86400;

	if (isNaN(dayDiff)) return '';

	if (mini) {
		// Return short format of time difference
		if (dayDiff < 0) {
			if (Math.abs(dayDiff) < 1) {
				if (Math.abs(diff) < 60) {
					return 'maintenant';
				} else if (Math.abs(diff) < 3600) {
					return `dans ${Math.floor(Math.abs(diff) / 60)} m`;
				} else if (Math.abs(diff) < 86400) {
					return `dans ${Math.floor(Math.abs(diff) / 3600)} h`;
				}
			}
			if (Math.abs(dayDiff) >= 1 && Math.abs(dayDiff) < 1.5) {
				return 'demain';
			} else if (Math.abs(dayDiff) < 7) {
				return 'dans {0} j', [Math.floor(Math.abs(dayDiff))];
			} else if (Math.abs(dayDiff) < 31) {
				return 'dans {0} sem', [Math.floor(Math.abs(dayDiff) / 7)];
			} else if (Math.abs(dayDiff) < 365) {
				return 'dans {0} M', [Math.floor(Math.abs(dayDiff) / 30)];
			} else {
				return 'dans {0} a', [Math.floor(Math.abs(dayDiff) / 365)];
			}
		} else if (dayDiff >= 0 && dayDiff < 1) {
			if (diff < 60) {
				return 'maintenant';
			} else if (diff < 3600) {
				return '{0} m', [Math.floor(diff / 60)];
			} else if (diff < 86400) {
				return '{0} h', [Math.floor(diff / 3600)];
			}
		} else {
			dayDiff = Math.floor(dayDiff);
			if (dayDiff < 7) {
				return '{0} j', [dayDiff];
			} else if (dayDiff < 31) {
				return '{0} sem', [Math.floor(dayDiff / 7)];
			} else if (dayDiff < 365) {
				return '{0} M', [Math.floor(dayDiff / 30)];
			} else {
				return '{0} a', [Math.floor(dayDiff / 365)];
			}
		}
	} else {
		// Return long format of time difference
		if (dayDiff < 0) {
			if (Math.abs(dayDiff) < 1) {
				if (Math.abs(diff) < 60) {
					return 'À l\'instant';
				} else if (Math.abs(diff) < 120) {
					return 'dans 1 minute';
				} else if (Math.abs(diff) < 3600) {
					return `dans ${Math.floor(Math.abs(diff) / 60)} minutes`;
				} else if (Math.abs(diff) < 7200) {
					return 'dans 1 heure';
				} else if (Math.abs(diff) < 86400) {
					return `dans ${Math.floor(Math.abs(diff) / 3600)} heures`;
				}
			}
			if (Math.abs(dayDiff) >= 1 && Math.abs(dayDiff) < 1.5) {
				return 'demain';
			} else if (Math.abs(dayDiff) < 7) {
				return 'dans {0} jours', [Math.floor(Math.abs(dayDiff))];
			} else if (Math.abs(dayDiff) < 31) {
				return 'dans {0} semaines', [Math.floor(Math.abs(dayDiff) / 7)];
			} else if (Math.abs(dayDiff) < 365) {
				return 'dans {0} mois', [Math.floor(Math.abs(dayDiff) / 30)];
			} else if (Math.abs(dayDiff) < 730) {
				return 'dans 1 an';
			} else {
				return 'dans {0} ans', [Math.floor(Math.abs(dayDiff) / 365)];
			}
		} else if (dayDiff >= 0 && dayDiff < 1) {
			if (diff < 60) {
				return 'À l\'instant';
			} else if (diff < 120) {
				return 'il y a 1 minute';
			} else if (diff < 3600) {
				return `il y a ${Math.floor(diff / 60)} minutes`;
			} else if (diff < 7200) {
				return 'il y a 1 heure';
			} else if (diff < 86400) {
				return `il y a ${Math.floor(diff / 3600)} heures`;
			}
		} else {
			dayDiff = Math.floor(dayDiff);
			if (dayDiff == 1) {
				return 'hier';
			} else if (dayDiff < 7) {
				return `il y a ${dayDiff} jours`;
			} else if (dayDiff < 14) {
				return 'il y a 1 semaine';
			} else if (dayDiff < 31) {
				return `il y a ${Math.floor(dayDiff / 7)} semaines`;
			} else if (dayDiff < 62) {
				return 'il y a 1 mois';
			} else if (dayDiff < 365) {
				return `il y a ${Math.floor(dayDiff / 30)} mois`;
			} else if (dayDiff < 730) {
				return 'il y a 1 an';
			} else {
				return `il y a ${Math.floor(dayDiff / 365)} ans`;
			}
		}
	}
}
