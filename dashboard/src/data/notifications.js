import { createResource } from 'frappe-ui'
import { getCurrentTeam } from './currentTeam'

export const unreadNotificationsCount = createResource({
	cache: ['Unread Notifications Count', getCurrentTeam()],
	url: 'press.api.notifications.get_unread_count',
	initialData: 0,
})

export const unreadSupportNotificationsCount = createResource({
	cache: ['Unread Support Notifications Count', getCurrentTeam()],
	url: 'press.api.notifications.get_unread_count',
	params: { type: 'Support Access' },
	initialData: 0,
})
