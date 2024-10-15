import { icon } from '../../../utils/components';
import { date } from '../../../utils/format';
import { Tab } from '../../common/types';

export function getLogsTab(forSite: boolean) {
	const childRoute = forSite ? 'Site Log' : 'Bench Log';
	const url = forSite ? 'press.api.site.logs' : 'press.api.bench.logs';

	return {
		label: 'Logs',
		icon: icon('file-text'),
		route: 'logs',
		childrenRoutes: [childRoute],
		type: 'list',
		list: {
			resource({ documentResource: res }) {
				return {
					params: {
						name: res.doc.group,
						bench: res.name
					},
					url,
					auto: true,
					cache: ['ObjectList', url, res.name]
				};
			},
			route(row) {
				return {
					name: childRoute,
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
	} satisfies Tab as Tab;
}
