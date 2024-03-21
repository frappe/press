import { icon } from '../../../utils/components';
import { date } from '../../../utils/format';

export function logsTab() {
	return {
		label: 'Logs',
		icon: icon('file-text'),
		route: 'logs',
		childrenRoutes: ['Site Log'],
		type: 'list',
		list: {
			resource({ documentResource: site }) {
				return {
					url: 'press.api.site.logs',
					params: {
						name: site.name
					},
					auto: true,
					cache: ['ObjectList', 'press.api.site.logs', site.name]
				};
			},
			route(row) {
				return {
					name: 'Site Log',
					params: { logName: row.name }
				};
			},
			columns: [
				{
					label: 'Name',
					fieldname: 'name'
				},
				{
					label: 'Size',
					fieldname: 'size',
					class: 'text-gray-600',
					format(value) {
						return `${value} kB`;
					}
				},
				{
					label: 'Created On',
					fieldname: 'created',
					format(value) {
						return value ? date(value, 'lll') : '';
					}
				}
			]
		}
	};
}
