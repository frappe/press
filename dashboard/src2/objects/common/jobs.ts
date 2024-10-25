import { unreachable } from '.';
import { getTeam } from '../../data/team';
import { icon } from '../../utils/components';
import { isMobile } from '../../utils/device';
import { duration } from '../../utils/format';
import { ColumnField, Tab } from './types';

type JobDocTypes = 'Site' | 'Bench' | 'Server' | 'Release Group';

export function getJobsTab(doctype: JobDocTypes) {
	const jobRoute = getJobRoute(doctype);

	return {
		label: 'Jobs',
		icon: icon('truck'),
		childrenRoutes: [jobRoute],
		route: 'jobs',
		type: 'list',
		list: {
			doctype: 'Agent Job',
			filters: res => {
				if (doctype === 'Site') return { site: res.name };
				else if (doctype === 'Bench') return { bench: res.name };
				else if (doctype === 'Server') return { server: res.name };
				else if (doctype === 'Release Group') return { group: res.name };
				throw unreachable;
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
			rowActions: ({ row }) => [
				{
					label: 'View in Desk',
					condition: () => getTeam()?.doc?.is_desk_user,
					onClick() {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/agent-job/${row.name}`,
							'_blank'
						);
					}
				}
			],
			columns: getJobTabColumns(doctype)
		}
	} satisfies Tab as Tab;
}

function getJobRoute(doctype: JobDocTypes) {
	if (doctype === 'Site') return 'Site Job';
	else if (doctype === 'Bench') return 'Bench Job';
	else if (doctype === 'Server') return 'Server Job';
	else if (doctype === 'Release Group') return 'Release Group Job';
	throw unreachable;
}

function getJobTabColumns(doctype: JobDocTypes) {
	const columns: ColumnField[] = [
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
			width: 1.2
		},
		{
			label: 'Duration',
			fieldname: 'duration',
			width: 0.35,
			format: (value, row) => {
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
	];

	if (doctype !== 'Site') return columns;
	return columns.filter(c => c.fieldname !== 'site');
}
