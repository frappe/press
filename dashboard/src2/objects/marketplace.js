import { defineAsyncComponent, h } from 'vue';
import { icon, renderDialog } from '../utils/components';
import GenericDialog from '../components/GenericDialog.vue';
import ObjectList from '../components/ObjectList.vue';
import NewAppDialog from '../components/marketplace/NewAppDialog.vue';
import ChangeAppBranchDialog from '../components/marketplace/ChangeAppBranchDialog.vue';
import { getTeam } from '../data/team';
import { toast } from 'vue-sonner';
import PlansDialog from '../components/marketplace/PlansDialog.vue';
import { confirmDialog } from '../utils/components';

export default {
	doctype: 'Marketplace App',
	whitelistedMethods: {
		removeVersion: 'remove_version',
		addVersion: 'add_version',
		disable: 'disable' // should come from Marketplace App Plan
	},
	list: {
		route: '/marketplace',
		title: 'Marketplace',
		fields: ['image', 'title', 'status', 'description'],
		columns: [
			{
				label: 'App',
				fieldname: 'title',
				width: 0.3,
				prefix(row) {
					return h('img', {
						src: row.image,
						class: 'w-6 h-6',
						alt: row.title
					});
				}
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
				route: 'analytics',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../components/marketplace/MarketplaceAppAnalytics.vue')
				),
				props: app => {
					return { app: { app: app.doc.name, title: app.doc.title } };
				}
			},
			{
				label: 'Versions',
				icon: icon('package'),
				route: 'versions',
				type: 'list',
				list: {
					doctype: 'Marketplace App Version',
					filters: app => {
						return { parent: app.doc.name, parenttype: 'Marketplace App' };
					},
					fields: ['name', 'version', 'source'],
					columns: [
						{
							label: 'Version',
							fieldname: 'version',
							width: 0.5
						},
						{
							label: 'Source',
							fieldname: 'source',
							width: 0.5
						},
						{
							label: 'Repository',
							fieldname: 'repository_owner',
							width: 0.5,
							format: (value, row) => {
								return `${value}/${row.repository}`;
							}
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: 0.5
						}
					],
					primaryAction({ listResource: versions, documentResource: app }) {
						return {
							label: 'New Version',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								renderDialog(
									h(
										GenericDialog,
										{
											options: {
												title: `Add a new version for ${app.doc.name}`,
												size: '2xl'
											}
										},
										{
											default: () =>
												h(ObjectList, {
													options: {
														label: 'Version',
														fieldname: 'version',
														fieldtype: 'ListSelection',
														columns: [
															{
																label: 'Version',
																fieldname: 'version'
															},
															{
																label: 'Branch',
																type: 'Select',
																fieldname: 'branch',
																format: (value, row) => {
																	row.selectedOption = value[0];
																	return value.map(v => ({
																		label: v,
																		value: v,
																		onClick: () => {
																			row.selectedOption = v;
																		}
																	}));
																}
															},
															{
																label: '',
																fieldname: '',
																align: 'right',
																type: 'Button',
																width: '5rem',
																Button({ row }) {
																	return {
																		label: 'Add',
																		onClick() {
																			if (app.addVersion.loading) return;
																			toast.promise(
																				app.addVersion.submit({
																					version: row.version,
																					branch: row.selectedOption
																				}),
																				{
																					loading: 'Adding new version...',
																					success: () => {
																						versions.reload();
																						return 'New version added';
																					},
																					error: e => {
																						return e.messages.length
																							? e.messages.join('\n')
																							: e.message;
																					}
																				}
																			);
																		}
																	};
																}
															}
														],
														resource() {
															return {
																url: 'press.api.marketplace.options_for_version',
																params: {
																	name: app.doc.name,
																	source: versions.data[0].source
																},
																auto: true
															};
														}
													}
												})
										}
									)
								);
							}
						};
					},
					rowActions({ row, listResource: versions, documentResource: app }) {
						return [
							{
								label: 'Change Branch',
								onClick() {
									renderDialog(
										h(ChangeAppBranchDialog, {
											app: app.doc.name,
											source: row.source,
											version: row.version,
											activeBranch: row.branch,
											onBranchChanged() {
												versions.reload();
											}
										})
									);
								}
							},
							{
								label: 'Remove Version',
								onClick() {
									toast.promise(app.removeVersion.submit(row.version), {
										loading: 'Removing version...',
										success: () => {
											versions.reload();
											return 'Version removed successfully';
										},
										error: e => {
											return e.messages.length
												? e.messages.join('\n')
												: e.message;
										}
									});
								}
							}
						];
					}
				}
			},
			// {
			// 	label: 'Installs',
			// 	icon: icon('download'),
			// 	route: 'install',
			// 	type: 'list',
			// 	comopnent: defineAsyncComponent(() =>
			// 	h(ObjectList, {
			// 		options: {
			// 			label: 'Site',
			// 			fieldname: 'site',
			// 				columns: [
			// 					{
			// 						label: 'Site',
			// 						fieldname: 'site',
			// 						width: 0.5
			// 					},
			// 					{
			// 						label: 'Plan',
			// 						fieldname: 'plan',
			// 						width: 0.5
			// 					},
			// 					{
			// 						label: 'Contact',
			// 						fieldname: 'email',
			// 						width: 0.5
			// 					}
			// 				],
			// 				resource() {
			// 					return {
			// 						url: 'press.api.marketplace.site_installs',
			// 						params: {
			// 							name: app.doc.name
			// 						},
			// 						auto: true
			// 					}
			// 				}
			// 			}
			// 		},
			// 	))
			// },
			{
				label: 'Pricing',
				icon: icon('dollar-sign'),
				route: 'pricing',
				type: 'list',
				list: {
					doctype: 'Marketplace App Plan',
					filters: app => {
						return { app: app.doc.name };
					},
					fields: ['name', 'title', 'price_inr', 'price_usd', 'enabled'],
					columns: [
						{
							label: 'Title',
							fieldname: 'title'
						},
						{
							label: 'Enabled',
							type: 'Badge',
							fieldname: 'enabled',
							format: value => {
								return value == 1 ? 'Enabled' : 'Disabled';
							}
						},
						{
							label: 'Price (INR)',
							fieldname: 'price_inr',
							format: value => {
								return `₹ ${value}`;
							}
						},
						{
							label: 'Price (USD)',
							fieldname: 'price_usd',
							format: value => {
								return `$ ${value}`;
							}
						}
					],
					primaryAction({ listResource: plans, documentResource: app }) {
						return {
							label: 'New Plan',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								renderDialog(
									h(PlansDialog, {
										app: app.doc.name,
										onPlanCreated() {
											plans.reload();
										}
									})
								);
							}
						};
					},
					rowActions({ row, listResource: plans, documentResource: app }) {
						return [
							{
								label: 'Edit',
								onClick() {
									renderDialog(
										h(PlansDialog, {
											app: app.doc.name,
											plan: row,
											onPlanUpdated() {
												plans.reload();
											}
										})
									);
								}
							}
						];
					}
				}
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
