export default {
	doctype: 'Press Notification',
	whitelistedMethods: {},
	list: {
		route: '/notifications',
		title: 'Notifications',
		fields: ['title'],
		orderBy: 'creation desc',
		columns: [
			{
				label: 'Title',
				fieldname: 'title'
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 }
		]
	},
	routes: []
};
