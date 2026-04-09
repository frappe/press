import { createResource } from 'frappe-ui';

export const unreadNotificationsCount = createResource({
	cache: 'Unread Notifications Count',
	url: 'press.api.notifications.get_unread_count',
	initialData: 0,
});

export const unreadSupportNotificationsCount = createResource({
	cache: 'Unread Support Notifications Cunt',
	url: 'press.api.notifications.get_unread_count',
	params: {
		type: 'Support Access',
	},
	initialData: 0,
});
