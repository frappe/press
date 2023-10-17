import { toast } from 'vue-sonner';
import { formatBytes } from '../utils/format';
import { frappeRequest } from 'frappe-ui';
import { defineAsyncComponent } from 'vue';

export default {
	doctype: 'Site',
	list: {
		route: '/sites',
		title: 'Sites',
		columns: [
			{ label: 'Site', fieldname: 'name', type: 'Data' },
			{ label: 'Status', fieldname: 'status', type: 'Badge' },
			{ label: 'Cluster', fieldname: 'cluster', type: 'Data' },
			{ label: 'Bench', fieldname: 'group', type: 'Data' },
			{ label: 'Plan', fieldname: 'plan', type: 'Data' }
		]
	},
	detail: {
		titleField: 'name',
		route: '/sites/:name',
		tabs: [
			{
				label: 'Analytics',
				route: 'analytics',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../../src/views/site/SiteCharts.vue')
				),
				props: site => {
					return { site: site.doc };
				}
			},
			{
				label: 'Apps',
				route: 'apps',
				type: 'list',
				list: {
					url: 'press.api.site.installed_apps',
					doctype: 'Site App',
					filters: site => {
						return { site: site.doc.name };
					},
					columns: [
						{
							label: 'App',
							fieldname: 'app',
							width: '12rem'
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: '12rem'
						},
						{
							label: 'Commit',
							fieldname: 'hash',
							type: 'Badge',
							width: '12rem',
							format(value) {
								return value.slice(0, 7);
							}
						},
						{
							label: 'Commit Message',
							fieldname: 'commit_message'
						}
					]
				}
			},
			{
				label: 'Domains',
				route: 'domains',
				type: 'list',
				list: {
					doctype: 'Site Domain',
					filters: site => {
						return { site: site.doc.name };
					},
					columns: [
						{
							label: 'Domain',
							fieldname: 'domain'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge'
						},
						{
							label: 'Primary',
							fieldname: 'primary',
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						},
						{
							label: 'DNS Type',
							fieldname: 'dns_type',
							type: 'Badge'
						}
					]
				}
			},
			{
				label: 'Backups',
				route: 'backups',
				type: 'list',
				list: {
					doctype: 'Site Backup',
					filters: site => {
						return {
							site: site.doc.name,
							files_availability: 'Available',
							status: ['in', ['Pending', 'Running', 'Success']]
						};
					},
					orderBy: 'creation desc',
					fields: [
						'status',
						'database_url',
						'public_url',
						'private_url',
						'config_file_url',
						'site'
					],
					columns: [
						{
							label: 'Timestamp',
							fieldname: 'creation',
							width: 0.8,
							format(value) {
								let timestamp = new Date(value);
								return `Backup on ${timestamp.toLocaleDateString()} at ${timestamp.toLocaleTimeString()}`;
							}
						},

						{
							label: 'Database',
							fieldname: 'database_size',
							width: 0.5,
							format(value) {
								return value ? formatBytes(value) : '';
							}
						},
						{
							label: 'Public Files',
							fieldname: 'public_size',
							width: 0.5,
							format(value) {
								return value ? formatBytes(value) : '';
							}
						},
						{
							label: 'Private Files',
							fieldname: 'private_size',
							width: 0.5,
							format(value) {
								return value ? formatBytes(value) : '';
							}
						},
						{
							label: 'Backup with files',
							fieldname: 'with_files',
							type: 'Icon',
							width: 0.5,
							Icon(value) {
								return value ? 'check' : '';
							}
						},
						{
							label: 'Offsite Backup',
							fieldname: 'offsite',
							width: 0.5,
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						}
					],
					rowActions(row) {
						if (row.status != 'Success') return;

						async function downloadBackup(backup, file) {
							// file: database, public, or private
							let link = backup.offsite
								? await frappeRequest('press.api.site.get_backup_link', {
										name: backup.site,
										backup: backup.name,
										file
								  })
								: backup[file + '_url'];
							window.open(link);
						}

						return [
							{
								label: 'Download Database',
								onClick() {
									return downloadBackup(row, 'database');
								}
							},
							{
								label: 'Download Public',
								onClick() {
									return downloadBackup(row, 'public');
								}
							},
							{
								label: 'Download Private',
								onClick() {
									return downloadBackup(row, 'private');
								}
							},
							{
								label: 'Download Config',
								onClick() {
									return downloadBackup(row, 'config_file');
								}
							}
						];
					},
					primaryAction({ listResource: backups, documentResource: site }) {
						return {
							label: 'Schedule Backup',
							loading: backups.insert.loading,
							onClick() {
								return backups.insert.submit(
									{
										site: site.doc.name
									},
									{
										onError(e) {
											let messages = e.messages || ['Something went wrong'];
											for (let message of messages) {
												toast.error(message);
											}
										},
										onSuccess() {
											toast.success('Backup scheduled');
										}
									}
								);
							}
						};
					}
				}
			},
			{
				label: 'Activity',
				route: 'activity',
				type: 'list',
				list: {
					doctype: 'Site Activity',
					filters: site => {
						return { site: site.doc.name };
					},
					fields: ['owner'],
					orderBy: 'creation desc',
					columns: [
						{
							label: 'Action',
							fieldname: 'action',
							format(value, row) {
								let action = row.action;
								if (action == 'Create') {
									action = 'Site created';
								}
								return `${action} by ${row.owner}`;
							}
						},
						{
							label: 'Reason',
							fieldname: 'reason'
						},
						{
							label: 'Timestamp',
							fieldname: 'creation',
							type: 'Timestamp'
						}
					]
				}
			},
			{
				label: 'Settings',
				route: 'settings'
			}
		]
	}
};
