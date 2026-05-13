import { dayjsLocal } from './dayjs';
import { plural } from './format';

export function trialDays(_trialEndDate) {
	const trialEndDate = dayjsLocal(_trialEndDate);
	const today = dayjsLocal();
	const diffHours = trialEndDate.diff(today, 'hours');
	const diffDays = trialEndDate
		.startOf('day')
		.diff(today.startOf('day'), 'day');
	let statusText = '';
	const isExpired = diffHours < 0;
	if (isExpired) {
		const absDays = Math.abs(diffDays);
		if (absDays === 0) {
			statusText = `earlier today`;
		} else {
			statusText = `${absDays} ${plural(absDays, 'day', 'days')} ago`;
		}
	} else if (diffHours < 1) {
		statusText = 'in less than an hour';
	} else if (diffHours < 24) {
		statusText = `in ${diffHours} ${plural(diffHours, 'hour', 'hours')}`;
	} else if (diffDays === 1) {
		statusText = 'tomorrow';
	} else {
		statusText = `in ${diffDays} ${plural(diffDays, 'day', 'days')}`;
	}
	return isExpired ? `Trial ended ${statusText}` : `Trial ends ${statusText}`;
}

export function isTrialEnded(_trialEndDate) {
	let trialEndDate = dayjsLocal(_trialEndDate);
	let today = dayjsLocal();
	return trialEndDate.isBefore(today, 'day');
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
