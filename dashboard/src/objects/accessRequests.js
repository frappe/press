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
		fields: ['target_team'],
		filters: {
			source: 'Received',
		},
		filterControls() {
			return [
				{
					type: 'tab',
					fieldname: 'source',
					options: ['Received', 'Sent'],
					default: 'Received',
				},
			];
		},
		onRowClick(row) {
			const team = getTeam();
			const isPending = row.status === 'Pending';
			const isReceived = row.target_team === team.doc?.name;
			isPending &&
				isReceived &&
				renderDialog(
					h(SupportAccessDialog, {
						name: row.name,
						requestedBy: row.requested_by,
						resourceType: row.resource_type,
						resourceName: row.resource_name,
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
				label: 'Resource Type',
				fieldname: 'resource_type',
			},
			{
				label: 'Resource Name',
				fieldname: 'resource_name',
			},
			{
				label: 'Duration in Hours',
				fieldname: 'allowed_for',
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
