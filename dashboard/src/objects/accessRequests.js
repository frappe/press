import { h } from 'vue';
import { renderDialog } from '../utils/components';
import SupportAccessDialog from '../components/SupportAccessDialog.vue';
import { getTeam } from '../data/team';

export default {
	doctype: 'Support Access',
	whitelistedMethods: {},
	list: {
		route: '/access-requests',
		title: 'Access Requests',
		orderBy: 'creation desc',
		fields: ['target_team', 'reason', 'site_domains', 'login_as_administrator'],
		filters: {
			source: 'Received',
		},
		filterControls() {
			const team = getTeam();

			return [
				{
					type: 'tab',
					fieldname: 'source',
					options: ['Received', 'Sent'],
					default: 'Received',
					condition: team.doc?.can_request_access,
				},
				{
					type: 'select',
					fieldname: 'status',
					options: ['', 'Pending', 'Accepted', 'Rejected'],
					default: '',
					placeholder: 'Status',
					condition: true,
				},
			].filter(({ condition }) => !!condition);
		},
		onRowClick(row) {
			renderDialog(
				h(SupportAccessDialog, {
					name: row.name,
				}),
			);
		},
		columns: [
			{
				label: 'Requested By',
				fieldname: 'requested_by',
			},
			{
				label: 'Status',
				fieldname: 'status',
				type: 'Badge',
				theme: (value) => {
					return {
						Pending: 'gray',
						Accepted: 'green',
						Rejected: 'red',
					}[value];
				},
			},
			{
				label: 'Resource',
				fieldname: 'resource_name',
				format: (_, row) => {
					if (row.resource_count > 1) {
						return row.resource_count + ' Resources';
					} else {
						return row.resource_name;
					}
				},
			},
			{
				label: 'Expiry',
				fieldname: 'access_allowed_till',
				type: 'Timestamp',
			},
			{
				label: 'Requested',
				fieldname: 'creation',
				type: 'Timestamp',
				align: 'right',
			},
		],
	},
};
