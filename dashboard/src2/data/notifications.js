import { createResource } from 'frappe-ui';

export const unreadNotificationsCount = createResource({
	cache: 'Unread Notifications Count',
	url: 'press.api.notifications.get_unread_count',
	initialData: 0,
	auto: true
});
