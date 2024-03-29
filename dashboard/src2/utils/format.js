import dayjs, { dayjsLocal } from '../utils/dayjs';
import { getTeam } from '../data/team';

export function bytes(bytes, decimals = 2, current = 0) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

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

export function plural(number, singular, plural) {
	if (number === 1) {
		return singular;
	}
	return plural;
}

export function planTitle(plan) {
	if (plan === undefined) return;
	let $team = getTeam();
	let india = $team.doc.country == 'India';
	let price_field = india ? 'price_inr' : 'price_usd';
	let price =
		plan?.block_monthly == 1 ? plan[price_field] * 12 : plan[price_field];
	return price > 0 ? `${userCurrency(price)}` : plan.plan_title;
}

export function userCurrency(value, fractions = 2) {
	let $team = getTeam();
	return currency(value, $team.doc.currency, fractions);
}

export function currency(value, currency, fractions = 2) {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency,
		maximumFractionDigits: fractions
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
