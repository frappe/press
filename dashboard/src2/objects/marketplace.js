import { defineAsyncComponent, h } from 'vue';
import { icon, renderDialog } from '../utils/components';
import NewAppDialog from '../components/marketplace/NewAppDialog.vue';
import { getTeam } from '../data/team';

export default {
	doctype: 'Marketplace App',
	whitelistedMethods: {},
	list: {
		route: '/marketplace',
		title: 'Marketplace',
		fields: ['image', 'title', 'status', 'description'],
		columns: [
			{
				label: 'Logo',
				type: 'Image',
				fieldname: 'image',
				width: 0.2
			},
			{
				label: 'Title',
				fieldname: 'title',
				width: 0.3
			},
			{
				label: 'Status',
				type: 'Badge',
				fieldname: 'status',
				width: 0.3
			},
			{
				label: 'Description',
				fieldname: 'description',
				width: 0.5
			}
		],
		primaryAction({ listResource: marketplace }) {
			return {
				label: 'New Marketplace App',
				variant: 'solid',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					renderDialog(h(NewAppDialog, {}));
				}
			};
		}
	},
	detail: {
		titleField: 'name',
		route: '/marketplace/:name',
		statusBadge({ documentResource: app }) {
			return { label: app.doc.status };
		},
		tabs: [
			{
				label: 'Listing',
				icon: icon('home'),
				route: 'overview',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../components/MarketplaceAppOverview.vue')
				),
				props: app => {
					return { app: app };
				}
			},
			{
				label: 'Analytics',
				icon: icon('bar-chart-2'),
				route: 'analytics'
			},
			{
				label: 'Versions', // -> Releases
				icon: icon('package'),
				route: 'versions'
			},
			{
				label: 'Pricing',
				icon: icon('dollar-sign'),
				route: 'pricing'
			},
			{
				label: 'Subscriptions',
				icon: icon('users'),
				route: 'subscription',
				type: 'list',
				list: {
					doctype: 'Subscription',
					filters: app => {
						return {
							document_type: 'Marketplace App',
							document_name: app.name
						};
					},
					fields: ['site', 'enabled', 'team'],
					columns: [
						{
							label: 'Site',
							fieldname: 'site',
							width: 0.6
						},
						{
							label: 'Status',
							type: 'Badge',
							fieldname: 'enabled',
							width: 0.3,
							format: value => {
								return value ? 'Active' : 'Disabled';
							}
						},
						{
							label: 'Price',
							fieldname: 'price',
							width: 0.3,
							format: value => {
								let $team = getTeam();
								let currencySymbol = $team.doc.currency == 'INR' ? '₹' : '$';
								return currencySymbol + value + '/month';
							}
						},
						{
							label: 'Active For',
							fieldname: 'active_for',
							width: 0.3,
							format: value => {
								return value + (value == 1 ? ' day' : ' days');
							}
						},
						{
							label: 'Contact',
							fieldname: 'email',
							width: 0.6,
							link: (value, _) => {
								return `mailto:${value}`;
							}
						}
					]
				}
			}
		],
		actions(context) {
			let { documentResource: app } = context;

			return [
				{
					label: 'View in Marketplace',
					slots: {
						prefix: icon('external-link')
					},
					condition: () => app.doc.status === 'Published',
					onClick() {
						window.open(
							`${window.location.origin}/marketplace/apps/${app.name}`,
							'_blank'
						);
					}
				}
			];
		}
	}
};
