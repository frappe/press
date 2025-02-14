import dayjs, { dayjsLocal } from '../utils/dayjs';
import { getTeam } from '../data/team';
import { format } from 'sql-formatter';

export function bytes(bytes, decimals = 2, current = 0) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	let i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
	if (i < 0) i++;

	return (
		parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i + current]
	);
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

export function plural(number, singular, plural) {
	if (typeof number === 'string') {
		number = parseInt(number);
	}
	if (number === 1) {
		return singular;
	}
	return plural;
}

export function planTitle(plan) {
	if (plan === undefined) return;
	const $team = getTeam();
	const india = $team.doc?.currency === 'INR';
	const priceField = india ? 'price_inr' : 'price_usd';
	const price =
		plan?.block_monthly == 1 ? plan[priceField] * 12 : plan[priceField];
	return price > 0 ? `${userCurrency(price, 0)}` : plan.plan_title;
}

export function userCurrency(value, fractions = 2) {
	const $team = getTeam();
	if (!$team.doc?.currency) return value;
	return currency(value, $team.doc?.currency, fractions);
}

export function currency(value, currency, fractions = 2) {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency,
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

export function pricePerDay(price) {
	let daysInThisMonth = dayjs().daysInMonth();
	return price / daysInThisMonth;
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
	return commaSeparator(arr, 'and');
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
		case 'sql':
			return formatSQL(value);
		default:
			return value;
	}
}
