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
			const team = getTeam();
			const isReceived = row.target_team === team.doc?.name;
			renderDialog(
				h(SupportAccessDialog, {
					name: row.name,
					requestedBy: row.requested_by,
					resourceType: row.resource_type,
					resourceName: row.resource_name,
					status: row.status,
					reason: row.reason,
					loginAsAdministrator: row.login_as_administrator,
					siteDomains: row.site_domains,
					isReceived,
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
