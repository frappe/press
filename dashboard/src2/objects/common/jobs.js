import { icon } from '../../utils/components';
import { isMobile } from '../../utils/device';
import { duration } from '../../utils/format';

function getJobRoute(doctype) {
	if (doctype === 'Site') return 'Site Job';
	else if (doctype === 'Server') return 'Server Job';
	else if (doctype === 'Release Group') return 'Release Group Job';
}

export function jobTab(doctype) {
	const jobRoute = getJobRoute(doctype);

	return {
		label: 'Jobs',
		icon: icon('truck'),
		childrenRoutes: [jobRoute],
		route: 'jobs',
		type: 'list',
		list: {
			doctype: 'Agent Job',
			filters: d => {
				if (doctype === 'Site') return { site: d.name };
				else if (doctype === 'Server') return { server: d.name };
				else if (doctype === 'Release Group') return { group: d.name };
			},
			route(row) {
				return {
					name: jobRoute,
					params: { id: row.name }
				};
			},
			orderBy: 'creation desc',
			searchField: 'job_type',
			fields: ['end', 'job_id'],
			filterControls() {
				return [
					{
						type: 'select',
						label: 'Status',
						fieldname: 'status',
						class: !isMobile() ? 'w-24' : '',
						options: ['', 'Pending', 'Running', 'Success', 'Failure']
					},
					{
						type: 'link',
						label: 'Type',
						fieldname: 'job_type',
						options: {
							doctype: 'Agent Job Type',
							orderBy: 'name asc',
							pageLength: 100
						}
					}
				];
			},
			columns: [
				{
					label: 'Job Type',
					fieldname: 'job_type',
					class: 'font-medium'
				},
				{
					label: 'Status',
					fieldname: 'status',
					type: 'Badge',
					width: 0.5
				},
				{
					label: 'Site',
					fieldname: 'site',
					width: 1.2,
					condition: () => doctype !== 'Site'
				},
				{
					label: 'Duration',
					fieldname: 'duration',
					width: 0.35,
					format(value, row) {
						if (row.job_id === 0 || !row.end) return;
						return duration(value);
					}
				},
				{
					label: 'Created By',
					fieldname: 'owner'
				},
				{
					label: '',
					fieldname: 'creation',
					type: 'Timestamp',
					width: 0.5,
					align: 'right'
				}
			].filter(c => (c.condition ? c.condition() : true))
		}
	};
}
