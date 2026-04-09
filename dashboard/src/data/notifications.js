import { createResource } from 'frappe-ui';

export const unreadNotificationsCount = createResource({
	cache: 'Unread Notifications Count',
	url: 'press.api.notifications.get_unread_count',
	initialData: 0,
});

export const unreadSupportNotificationsCount = createResource({
	cache: 'Unread Support Notifications Count',
	url: 'press.api.notifications.get_support_unread_count',
	initialData: 0,
});
