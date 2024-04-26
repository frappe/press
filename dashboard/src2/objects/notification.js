import { h } from 'vue';
import router from '../router';
import { getDocResource } from '../utils/resource';
import { Tooltip } from 'frappe-ui';
import { icon } from '../utils/components';

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
				width: '15rem',
				format(value, row) {
					return value || row.type;
				},
				suffix(row) {
					if (row.is_actionable && !row.is_addressed) {
						let AlertIcon = icon('alert-circle');
						return h(
							Tooltip,
							{
								text: 'This notifcation requires your attention'
							},
							{
								default: () =>
									h(
										'div',
										{
											class: 'ml-2  text-red-500'
										},
										h(AlertIcon)
									)
							}
						);
					}
				}
			},
			{
				label: 'Message',
				fieldname: 'message',
				type: 'Component',
				width: '65%',
				component({ row }) {
					return h('div', {
						class: 'truncate text-base text-gray-600',
						innerHTML: row.message.split('\n')[0]
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
