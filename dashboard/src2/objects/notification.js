import { h } from 'vue';
import router from '../router';
import { getDocResource } from '../utils/resource';

export default {
	doctype: 'Press Notification',
	whitelistedMethods: {},
	list: {
		resource() {
			return {
				type: 'list',
				doctype: 'Press Notification',
				url: 'press.api.notifications.get_notifications',
				auto: true,
				filters: {},
				cache: ['Notifications']
			};
		},
		route: '/notifications',
		title: 'Notifications',
		orderBy: 'creation desc',
		filterControls() {
			return [
				{
					type: 'select',
					label: 'Read',
					class: 'w-20',
					fieldname: 'read',
					options: ['', 'Read', 'Unread']
				}
			];
		},
		onRowClick(row) {
			let notification = getDocResource({
				doctype: 'Press Notification',
				name: row.name,
				whitelistedMethods: {
					markNotificationAsRead: 'mark_as_read'
				}
			});
			notification.markNotificationAsRead.submit().then(() => {
				if (row.route) router.push(row.route);
			});
		},
		columns: [
			{
				label: 'Title',
				fieldname: 'title',
				width: '12rem',
				format(value, row) {
					return value || row.type;
				}
			},
			{
				label: 'Message',
				fieldname: 'message',
				type: 'Component',
				component({ row }) {
					return h('div', {
						class: 'truncate text-base text-gray-600',
						innerHTML: row.message
					});
				}
			},
			{
				label: '',
				fieldname: 'creation',
				type: 'Timestamp',
				align: 'right',
				width: '10rem'
			}
		]
	},
	routes: []
};
