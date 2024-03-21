import HelpIcon from '~icons/lucide/help-circle';
import { defineAsyncComponent, h } from 'vue';
import { Button } from 'frappe-ui';
import ServerActions from '../components/server/ServerActions.vue';
import { userCurrency, bytes, pricePerDay, planTitle } from '../utils/format';
import { icon } from '../utils/components';
import { duration } from '../utils/format';
import { getTeam } from '../data/team';
import { tagTab } from './common/tags';
import router from '../router';

export default {
	doctype: 'Cluster',
	list: {
		route: '/clusters',
		title: 'Cluster',
		orderBy: 'creation desc',
		columns: [
			{
				label: 'Name',
				fieldname: 'title',
				width: 1
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 },
			{ label: 'Description', fieldname: 'description', width: 2 },
			{ label: 'Provider', fieldname: 'cloud_provider', width: 1 },
			{
				label: 'Created On',
				fieldname: 'creation',
				type: 'Timestamp',
				width: 1
			}
		],
		primaryAction({ listResource: servers }) {
			return {
				label: 'New Cluster',
				variant: 'solid',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					router.push({ name: 'New Cluster' });
				}
			};
		}
	},
	detail: {
		titleField: 'name',
		route: '/clusters/:name',
		statusBadge({ documentResource: cluster }) {
			return {
				label: cluster.doc.status
			};
		},
		actions({ documentResource: server }) {
			let $team = getTeam();

			return [
				{
					label: 'Options',
					button: {
						label: 'Options',
						slots: {
							icon: icon('more-horizontal')
						}
					},
					options: [
						{
							label: 'View in Desk',
							icon: icon('external-link'),
							condition: () => $team.doc.is_desk_user,
							onClick() {
								window.open(
									`${window.location.protocol}//${
										window.location.host
									}/app/${server.doctype.replace(' ', '-').toLowerCase()}/${
										server.doc.name
									}`,
									'_blank'
								);
							}
						}
					]
				}
			];
		},
		tabs: [
			{
				label: 'Overview',
				icon: icon('home'),
				route: 'overview',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../components/cluster/ClusterOverview.vue')
				),
				props: cluster => {
					return { cluster: cluster.doc.name };
				}
			},
			{
				label: 'Severs',
				icon: icon('package'),
				route: 'servers',
				type: 'list',
				list: {
					doctype: 'Server',
					filters: cluster => {
						return { cluster: cluster.doc.name };
					},
					columns: [
						{ label: 'Title', fieldname: 'title' },
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5
						}
					],
					route(row) {
						return {
							name: 'Server Detail',
							params: { name: row.name }
						};
					},
					primaryAction({ listResource: servers, documentResource: cluster }) {
						return {
							label: 'New Server',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								router.push({
									name: 'New Server',
									params: { cluster: cluster.doc.name }
								});
							}
						};
					}
				}
			},
			tagTab()
		]
	}
};
