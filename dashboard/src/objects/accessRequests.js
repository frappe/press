export default {
	doctype: 'Support Access',
	whitelistedMethods: {},
	list: {
		route: '/access-requests',
		title: 'Access Requests',
		orderBy: 'creation desc',
		columns: [
			{
				label: 'Requested By',
				fieldname: 'requested_by',
			},
			{
				label: 'Status',
				fieldname: 'status',
				type: 'Badge',
			},
			{
				label: 'Hours',
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
