import { dayjsLocal } from './dayjs';
import { plural } from './format';

export function trialDays(_trialEndDate) {
	let trialEndDate = dayjsLocal(_trialEndDate);
	let today = dayjsLocal();
	let diffHours = trialEndDate.diff(today, 'hours');
	let endsIn = '';
	if (diffHours < 0) {
		let daysAgo = Math.floor(Math.abs(diffHours) / 24);
		endsIn = `${daysAgo} ${plural(daysAgo, 'day', 'days')} ago`;
	} else if (diffHours < 24) {
		endsIn = `today`;
	} else {
		let days = Math.round(diffHours / 24);
		endsIn = `in ${days} ${plural(days, 'day', 'days')}`;
	}
	if (trialEndDate.isAfter(today) || trialEndDate.isSame(today, 'day')) {
		return `Trial ends ${endsIn}`;
	} else {
		return `Trial ended ${endsIn}`;
	}
}
