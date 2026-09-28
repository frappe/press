import { createResource } from 'frappe-ui';

export const unreadNotificationsCount = createResource({
	cache: 'Unread Notifications Count',
	url: 'press.api.notifications.get_unread_count',
	initialData: 0,
});

export const unreadSupportNotificationsCount = createResource({
	cache: 'Unread Support Notifications Count',
	url: 'press.api.notifications.get_unread_count',
	params: { type: 'Support Access' },
	initialData: 0,
});

export const markAllNotificationsAsRead = createResource({
	url: 'press.api.notifications.mark_all_notifications_as_read',
	onSuccess: () => {
		unreadNotificationsCount.reload();
		unreadSupportNotificationsCount.reload();
	},
});
