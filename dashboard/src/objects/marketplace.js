import { defineAsyncComponent, h } from 'vue';
import { Button, Badge, Combobox } from 'frappe-ui';
import { toast } from 'vue-sonner';
import ChangeAppBranchDialog from '../components/marketplace/ChangeAppBranchDialog.vue';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import PlansDialog from '../components/marketplace/PlansDialog.vue';
import CodeReview from '../components/marketplace/CodeReview.vue';
import GenericDialog from '../components/GenericDialog.vue';
import ObjectList from '../components/ObjectList.vue';
import { userCurrency, currency } from '../utils/format';
import { getToastErrorMessage } from '../utils/toast';
import { isMobile } from '../utils/device';
import router from '../router';

export default {
	doctype: 'Marketplace App',
	whitelistedMethods: {
		removeVersion: 'remove_version',
		addVersion: 'add_version',
		siteInstalls: 'site_installs',
		createApprovalRequest: 'create_approval_request',
		cancelApprovalRequest: 'cancel_approval_request',
		yankAppRelease: 'yank_app_release',
		unyankAppRelease: 'unyank_app_release',
		updateListing: 'update_listing',
		markAppReadyForReview: 'mark_app_ready_for_review',
	},
	list: {
		route: '/apps',
		title: 'Marketplace',
		fields: ['image', 'title', 'status', 'description'],
		columns: [
			{
				label: 'App',
				fieldname: 'title',
				class: 'font-medium',
				width: 0.6,
				prefix(row) {
					return row.image
						? h('img', {
								src: row.image,
								class: 'w-6 h-6 rounded-sm',
								alt: row.title,
							})
						: h(
								'div',
								{
									class:
										'w-6 h-6 rounded bg-gray-300 text-gray-600 flex items-center justify-center',
								},
								row.title[0].toUpperCase(),
							);
				},
			},
			{
				label: 'Status',
				type: 'Badge',
				fieldname: 'status',
				width: 0.3,
			},
			{
				label: 'Description',
				fieldname: 'description',
				width: '40rem',
			},
		],
		primaryAction() {
			return {
				label: 'New App',
				variant: 'solid',
				slots: {
					prefix: icon('plus'),
				},
				onClick() {
					const NewMarketplaceAppDialog = defineAsyncComponent(
						() =>
							import('../components/marketplace/NewMarketplaceAppDialog.vue'),
					);

					renderDialog(h(NewMarketplaceAppDialog));
				},
			};
		},
	},
	detail: {
		titleField: 'name',
		route: '/apps/:name',
		statusBadge({ documentResource: app }) {
			return { label: app.doc.status };
		},
		breadcrumbs({ items, documentResource: app }) {
			return [
				items[0],
				{
					label: app.doc.title,
					route: `/apps/${app.doc.name}`,
				},
			];
		},
		tabs: [
			{
				label: 'Analytics',
				icon: icon('bar-chart-2'),
				route: 'analytics',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/marketplace/MarketplaceAppAnalytics.vue'),
				),
				props: (app) => {
					return { app: app.doc.name };
				},
			},
			{
				label: 'Listing',
				icon: icon('shopping-cart'),
				route: 'listing',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/MarketplaceAppListing.vue'),
				),
				props: (app) => {
					return { app: app };
				},
			},
			{
				label: 'Versions',
				icon: icon('package'),
				route: 'versions',
				type: 'list',
				list: {
					doctype: 'Marketplace App Version',
					filters: (app) => {
						return { parent: app.doc.name, parenttype: 'Marketplace App' };
					},
					fields: [
						'source.repository_owner as repository_owner',
						'source.repository as repository',
						'source.branch as branch',
					],
					columns: [
						{
							label: 'Version',
							fieldname: 'version',
							width: 0.5,
						},
						{
							label: 'Source',
							fieldname: 'source',
							width: 0.5,
						},
						{
							label: 'Repository',
							width: 0.5,
							format: (value, row) => {
								return `${row.repository_owner}/${row.repository}`;
							},
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: 0.5,
						},
					],
					primaryAction({ listResource: versions, documentResource: app }) {
						return {
							label: 'New Version',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								renderDialog(
									h(
										GenericDialog,
										{
											options: {
												title: `Add version support for ${app.doc.title}`,
												size: '4xl',
											},
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
																fieldname: 'version',
															},
															{
																label: 'Branch',
																type: 'Component',
																component({ row }) {
																	if (!row.selectedOption) {
																		row.selectedOption = row.branch[0];
																	}
																	return h(Combobox, {
																		modelValue: row.selectedOption,
																		options: row.branch,
																		allowCustomValue: true,
																		'onUpdate:modelValue': (value) => {
																			row.selectedOption = value;
																		},
																	});
																},
															},
															{
																label: '',
																fieldname: '',
																align: 'right',
																type: 'Button',
																width: '5rem',
																Button({ row, listResource: versionsOptions }) {
																	return {
																		label: 'Add',
																		onClick() {
																			if (app.addVersion.loading) return;
																			toast.promise(
																				app.addVersion.submit({
																					version: row.version,
																					branch: row.selectedOption,
																				}),
																				{
																					loading: 'Adding new version...',
																					success: () => {
																						versions.reload();
																						versionsOptions.reload();
																						return 'New version added';
																					},
																					error: (e) => getToastErrorMessage(e),
																				},
																			);
																		},
																	};
																},
															},
														],
														resource() {
															return {
																url: 'press.api.marketplace.options_for_version',
																params: {
																	name: app.doc.name,
																},
																auto: true,
															};
														},
													},
												}),
										},
									),
								);
							},
						};
					},
					rowActions({ row, listResource: versions, documentResource: app }) {
						return [
							{
								label: 'Show Releases',
								slots: {
									prefix: icon('plus'),
								},
								onClick() {
									showReleases(row, app);
								},
							},
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
											},
										}),
									);
								},
							},
							{
								label: 'Remove Version',
								onClick() {
									toast.promise(
										app.removeVersion.submit({ version: row.version }),
										{
											loading: 'Removing version...',
											success: () => {
												versions.reload();
												return 'Version removed successfully';
											},
											error: (e) => getToastErrorMessage(e),
										},
									);
								},
							},
						];
					},
				},
			},
			{
				label: 'Pricing',
				icon: icon('dollar-sign'),
				route: 'pricing',
				type: 'list',
				list: {
					doctype: 'Marketplace App Plan',
					filters: (app) => {
						return { app: app.doc.name };
					},
					fields: ['name', 'title', 'price_inr', 'price_usd', 'enabled'],
					columns: [
						{
							label: 'Title',
							fieldname: 'title',
						},
						{
							label: 'Enabled',
							type: 'Badge',
							fieldname: 'enabled',
							format: (value) => {
								return value == 1 ? 'Enabled' : 'Disabled';
							},
						},
						{
							label: 'Price (INR)',
							fieldname: 'price_inr',
							format: (value) => {
								return currency(value, 'INR');
							},
						},
						{
							label: 'Price (USD)',
							fieldname: 'price_usd',
							format: (value) => {
								return currency(value, 'USD');
							},
						},
					],
					primaryAction({ listResource: plans, documentResource: app }) {
						return {
							label: 'New Plan',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								renderDialog(
									h(PlansDialog, {
										app: app.doc.name,
										onPlanCreated() {
											plans.reload();
										},
									}),
								);
							},
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
											},
										}),
									);
								},
							},
						];
					},
				},
			},
			{
				label: 'Subscriptions',
				icon: icon('users'),
				route: 'subscription',
				type: 'list',
				list: {
					doctype: 'Subscription',
					filters: (app) => {
						return {
							document_type: 'Marketplace App',
							document_name: app.name,
						};
					},
					fields: ['site', 'enabled', 'team'],
					filterControls() {
						return [
							{
								type: 'select',
								label: 'Status',
								class: !isMobile() ? 'w-24' : '',
								fieldname: 'enabled',
								options: ['', 'Active', 'Disabled'],
							},
						];
					},
					columns: [
						{
							label: 'Site',
							fieldname: 'site',
							width: 0.6,
						},
						{
							label: 'Status',
							type: 'Badge',
							fieldname: 'enabled',
							width: 0.3,
							format: (value) => {
								return value ? 'Active' : 'Disabled';
							},
						},
						{
							label: 'Price',
							fieldname: 'price',
							width: 0.3,
							format: (value) => {
								return userCurrency(value);
							},
						},
						{
							label: 'Active For',
							fieldname: 'active_for',
							width: 0.3,
							format: (value) => {
								return value + (value == 1 ? ' day' : ' days');
							},
						},
					],
				},
			},
		],
		actions({ documentResource: app }) {
			return [
				{
					label: 'View in Marketplace',
					slots: {
						prefix: icon('external-link'),
					},
					condition: () => app.doc.status === 'Published',
					onClick() {
						window.open(
							`${window.location.origin}/marketplace/apps/${app.name}`,
							'_blank',
						);
					},
				},
				{
					label: 'Guidelines',
					slots: {
						icon: icon('help-circle'),
					},
					condition: () => app.doc.status === 'Draft',
					onClick() {
						window.open(
							'https://docs.frappe.io/cloud/marketplace/marketplace-guidelines',
							'_blank',
						);
					},
				},
				{
					label: 'Complete Listing',
					variant: 'solid',
					slots: {
						prefix: icon('alert-circle'),
					},
					condition: () => app.doc.status === 'Draft',
					onClick() {
						let AppListingStepsDialog = defineAsyncComponent(
							() =>
								import('../components/marketplace/AppListingStepsDialog.vue'),
						);

						renderDialog(
							h(AppListingStepsDialog, {
								app: app.doc.name,
							}),
						);
					},
				},
				,
				{
					label: 'Options',
					condition: () => app.doc.status === 'Draft',
					options: [
						{
							label: 'Delete',
							icon: icon('trash-2'),
							condition: () => app.doc.status === 'Draft',
							onClick() {
								confirmDialog({
									title: `Delete App ${app.doc.title}`,
									message: 'Are you sure you want to delete this app?',
									onSuccess({ hide }) {
										toast.promise(app.delete.submit(), {
											loading: 'Deleting app...',
											success: () => {
												hide();
												router.push({ name: 'Marketplace App List' });
												return 'App deleted successfully';
											},
											error: (e) => getToastErrorMessage(e),
										});
									},
								});
							},
						},
					],
				},
			];
		},
	},
};

function showReleases(row, app) {
	renderDialog(
		h(
			GenericDialog,
			{
				options: {
					title: `Releases for ${app.doc.name} on ${row.branch} branch`,
					size: '6xl',
				},
			},
			{
				default: () =>
					h(ObjectList, {
						options: {
							label: 'Version',
							type: 'list',
							doctype: 'App Release',
							filters: {
								app: app.doc.name,
								source: row.source,
							},
							fields: ['message', 'tag', 'author', 'status'],
							orderBy: 'creation desc',
							columns: [
								{
									label: 'Commit Message',
									fieldname: 'message',
									class: 'truncate',
									width: 0.4,
									format: (value) => {
										return value.length > 50
											? `${value.slice(0, 50)}...`
											: value;
									},
								},
								{
									label: 'Hash',
									fieldname: 'hash',
									class: 'w-24',
									type: 'Badge',
									width: 0.15,
									align: 'center',
									format: (value) => {
										return value.slice(0, 7);
									},
								},
								{
									label: 'Author',
									fieldname: 'author',
									width: 0.15,
									align: 'center',
								},
								{
									label: 'Status',
									fieldname: 'status',
									type: 'Badge',
									width: 0.15,
									align: 'center',
								},
								{
									label: 'Code Screening',
									type: 'Component',
									width: 0.15,
									align: 'center',
									component: ({ row, listResource: releases, app }) => {
										if (
											(row.status === 'Awaiting Approval' ||
												row.status === 'Rejected') &&
											row.screening_status === 'Complete'
										) {
											return h(Button, {
												label: 'Code Review',
												variant: 'subtle',
												theme: 'blue',
												size: 'sm',
												onClick: () =>
													codeReview(row, app, window.is_system_user),
											});
										}
										return h(Badge, {
											label: row.screening_status || 'Not Started',
										});
									},
								},
								{
									label: '',
									fieldname: '',
									align: 'right',
									type: 'Button',
									width: 0.2,
									Button({ row, listResource: releases }) {
										let label = '';
										let successMessage = '';
										let loadingMessage = '';

										if (row.status == 'Approved') {
											label = 'Yank';
											successMessage = 'The release has been yanked';
											loadingMessage = 'Yanking release...';
										}
										if (row.status == 'Yanked') {
											label = 'Unyank';
											successMessage = 'The release has been unyanked';
											loadingMessage = 'Unyanking release...';
										}
										if (row.status === 'Awaiting Approval') {
											label = 'Cancel';
											successMessage = 'The release has been cancelled';
											loadingMessage = 'Cancelling release approval request...';
										} else if (row.status === 'Draft') {
											label = 'Submit';
											loadingMessage = 'Submitting release for approval...';
											successMessage =
												'The release has been submitted for approval';
										}

										return {
											label,
											onClick() {
												const actions = {
													Approved: () =>
														app.yankAppRelease.submit({
															app_release: row.name,
															hash: row.hash,
														}),
													AwaitingApproval: () =>
														app.cancelApprovalRequest.submit({
															app_release: row.name,
														}),
													Draft: () =>
														app.createApprovalRequest.submit({
															app_release: row.name,
														}),
													Yanked: () =>
														app.unyankAppRelease.submit({
															hash: row.hash,
														}),
												};

												const action = actions[row.status.replace(' ', '')];
												if (!action) return;

												toast.promise(action(), {
													loading: loadingMessage,
													success: () => {
														releases.reload();
														return successMessage;
													},
													error: (e) => getToastErrorMessage(e),
												});
											},
										};
									},
								},
							],
						},
					}),
			},
		),
	);
}

function codeReview(row, app, isSystemUser) {
	renderDialog(
		h(CodeReview, {
			row: row,
			app: app,
			isSystemUser: isSystemUser,
		}),
	);
}
