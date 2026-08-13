import { createResource } from 'frappe-ui'
import { defineAsyncComponent, h } from 'vue'
import { toast } from 'vue-sonner'
import router from '../../router'
import { confirmDialog, icon, renderDialog } from '../../utils/components'
import dayjs from '../../utils/dayjs'
import { bytes, date } from '../../utils/format'
import { getQueryParam, setQueryParam } from '../../utils/index'
import { getToastErrorMessage } from '../../utils/toast'
import { getUpsellBanner } from '../common'

export function getBackupsTab() {
	return {
		label: 'Backups',
		icon: icon('archive'),
		route: 'backups',
		type: 'Component',
		redirectTo: 'Site Backup List',
		childrenRoutes: ['Site Backup List', 'Site Backup Audit Trail'],
		nestedChildrenRoutes: [
			{
				name: 'Site Backup List',
				path: 'list',
				component: () => import('../../components/site/SiteBackupList.vue'),
			},
			{
				name: 'Site Backup Audit Trail',
				path: 'audit-trail',
				component: () =>
					import('../../components/site/SiteBackupAuditTrail.vue'),
			},
		],
		component: defineAsyncComponent(
			() => import('../../components/site/SiteBackups.vue'),
		),
	}
}

// The Site Backup records Press still holds. Kept as a plain options object so
// SiteBackups.vue can layer the history control on top without touching it.
export function backupRecordsOptions() {
	return {
		doctype: 'Site Backup',
		filters: (site) => {
			let filters = {
				site: site.doc?.name,
			}
			const backup_name = getQueryParam('name')
			if (backup_name) {
				filters.name = backup_name
			}
			return filters
		},
		orderBy: 'creation desc',
		fields: [
			'name',
			'job',
			'status',
			'database_url',
			'public_url',
			'private_url',
			'config_file_url',
			'site',
			'remote_database_file',
			'remote_public_file',
			'remote_private_file',
			'remote_config_file',
			'physical',
		],
		columns: [
			{
				label: 'Timestamp',
				fieldname: 'creation',
				width: 1,
				format(value) {
					return `Backup on ${date(value, 'llll')}`
				},
			},
			{
				label: 'Status',
				fieldname: 'status',
				width: '150px',
				align: 'center',
				type: 'Badge',
			},
			{
				label: 'Database',
				fieldname: 'database_size',
				width: 0.5,
				format(value) {
					return value ? bytes(value) : ''
				},
			},
			{
				label: 'Public Files',
				fieldname: 'public_size',
				width: 0.5,
				format(value) {
					return value ? bytes(value) : ''
				},
			},
			{
				label: 'Private Files',
				fieldname: 'private_size',
				width: 0.5,
				format(value) {
					return value ? bytes(value) : ''
				},
			},
			{
				label: 'Files',
				fieldname: 'with_files',
				type: 'Icon',
				width: 0.25,
				Icon(value) {
					return value ? 'check' : ''
				},
			},
			{
				label: 'Offsite',
				fieldname: 'offsite',
				width: 0.25,
				type: 'Icon',
				Icon(value) {
					return value ? 'check' : ''
				},
			},
			{
				label: 'Physical',
				fieldname: 'physical',
				width: 0.25,
				type: 'Icon',
				Icon(value) {
					return value ? 'check' : ''
				},
			},
		],
		searchField: getQueryParam('name') ? null : 'name',
		updateFilters({ name }) {
			setQueryParam('name', name)
		},
		autoReloadAfterUpdateFilterCallback: true,
		filterControls() {
			const backup_name = getQueryParam('name')
			let filters = backup_name
				? [
						{
							type: 'text',
							label: 'Backup Record',
							fieldname: 'name',
						},
					]
				: []
			filters = filters.concat([
				{
					type: 'checkbox',
					label: 'Physical Backups',
					fieldname: 'physical',
				},
				{
					type: 'checkbox',
					label: 'Offsite Backups',
					fieldname: 'offsite',
				},
			])
			return filters
		},
		rowActions({ row, documentResource: site }) {
			if (row.status != 'Success') return

			function getFileName(file) {
				if (file == 'database') return 'database'
				if (file == 'public') return 'public files'
				if (file == 'private') return 'private files'
				if (file == 'config') return 'config file'
			}

			function confirmDownload(backup, file) {
				confirmDialog({
					title: 'Download Backup',
					message: `You will be downloading the ${getFileName(
						file,
					)} backup of the site <b>${
						site.doc?.host_name || site.doc?.name
					}</b> that was created on ${date(backup.creation, 'llll')}.${
						!backup.offsite
							? '<br><br><div class="p-2 bg-surface-gray-2 rounded border-outline-gray-1">You have to be logged in as a <b>System Manager</b> <em>in your site</em> to download the backup.<div>'
							: ''
					}`,
					onSuccess({ hide }) {
						downloadBackup(backup, file, hide)
					},
				})
			}

			async function downloadBackup(backup, file, hide) {
				// file: database, public, or private
				if (backup.offsite) {
					site.getBackupDownloadLink.submit(
						{ backup: backup.name, file },
						{
							onSuccess(r) {
								hide()
								// TODO: fix this in documentResource, it should return message directly
								if (r.message) {
									window.open(r.message)
								}
							},
						},
					)
				} else {
					const url =
						file == 'config' ? backup.config_file_url : backup[file + '_url']

					const domainRegex = /^(https?:\/\/)?([^/]+)\/?/
					const newUrl = url.replace(domainRegex, `$1${site.doc.host_name}/`)
					hide()
					window.open(newUrl)
				}
			}

			return [
				{
					group: 'Details',
					items: [
						{
							label: 'View Job',
							onClick() {
								router.push({
									name: 'Site Job',
									params: { name: site.name, id: row.job },
								})
							},
						},
					],
				},
				{
					group: 'Download',
					condition: () => !row.physical,
					items: [
						{
							label: 'Download Database',
							onClick() {
								return confirmDownload(row, 'database')
							},
						},
						{
							label: 'Download Public',
							onClick() {
								return confirmDownload(row, 'public')
							},
							condition: () => row.public_url,
						},
						{
							label: 'Download Private',
							onClick() {
								return confirmDownload(row, 'private')
							},
							condition: () => row.private_url,
						},
						{
							label: 'Download Config',
							onClick() {
								return confirmDownload(row, 'config')
							},
							condition: () => row.config_file_url,
						},
					],
				},
				{
					group: 'Restore',
					condition: () => row.offsite || row.physical,
					items: [
						{
							label: 'Restore Backup',
							condition: () => site.doc.status !== 'Archived',
							onClick() {
								if (row.physical && row.ready_to_restore) {
									toast.error(
										'Physical Snapshot is not ready to restore. Try again after 10 minutes.',
									)
									return
								}

								if (row.physical) {
									confirmDialog({
										title: 'Restore Physical Backup',
										message: `Are you sure you want to restore your site's database from physical backup taken on <b>${dayjs(
											row.creation,
										).format('lll')}</b> ?`,
										onSuccess({ hide }) {
											toast.promise(
												site.restoreSiteFromPhysicalBackup.submit({
													backup: row.name,
												}),
												{
													loading: 'Scheduling physical backup restore...',
													success: () => {
														hide()
														router.push({
															name: 'Site Jobs',
															params: {
																name: site.name,
															},
														})
														return 'Backup restore scheduled successfully.'
													},
													error: (e) => getToastErrorMessage(e),
												},
											)
										},
									})
								} else {
									confirmDialog({
										title: 'Restore Backup',
										message: `Are you sure you want to restore your site to this offsite backup from <b>${dayjs(
											row.creation,
										).format('lll')}</b> ?`,
										onSuccess({ hide }) {
											toast.promise(
												site.restoreSiteFromFiles.submit({
													files: {
														database: row.remote_database_file,
														public: row.remote_public_file,
														private: row.remote_private_file,
														config: row.remote_config_file,
													},
												}),
												{
													loading: 'Scheduling backup restore...',
													success: (jobId) => {
														hide()
														router.push({
															name: 'Site Job',
															params: {
																name: site.name,
																id: jobId,
															},
														})
														return 'Backup restore scheduled successfully.'
													},
													error: (e) => getToastErrorMessage(e),
												},
											)
										},
									})
								}
							},
						},
						{
							label: 'Restore Backup on another Site',
							condition: () => !row.physical,
							onClick() {
								let SelectSiteForRestore = defineAsyncComponent(
									() =>
										import('../../components/site/SelectSiteForRestore.vue'),
								)
								renderDialog(
									h(SelectSiteForRestore, {
										site: site.name,
										database_backup_exists: Boolean(row.remote_database_file),
										public_backup_exists: Boolean(row.remote_public_file),
										private_backup_exists: Boolean(row.remote_private_file),
										config_backup_exists: Boolean(row.remote_config_file),
										onRestore({
											selectedSite,
											restoreDatabase,
											restorePublic,
											restorePrivate,
											restoreConfig,
										}) {
											const restoreSite = createResource({
												url: 'press.api.site.restore',
											})

											let payload = {
												name: selectedSite,
												files: {},
											}
											if (restoreDatabase) {
												payload.files.database = row.remote_database_file
											}
											if (restorePublic) {
												payload.files.public = row.remote_public_file
											}
											if (restorePrivate) {
												payload.files.private = row.remote_private_file
											}
											if (restoreConfig) {
												payload.files.config = row.remote_config_file
											}

											// check if any file is selected
											if (Object.keys(payload.files).length === 0) {
												toast.error(
													'No backup files selected. Select at least one file (database, public, private, or config) to restore.',
												)
												return
											}

											return toast.promise(restoreSite.submit(payload), {
												loading: 'Scheduling backup restore...',
												success: (jobId) => {
													router.push({
														name: 'Site Job',
														params: { name: selectedSite, id: jobId },
													})
													return 'Backup restore scheduled successfully.'
												},
												error: (e) => getToastErrorMessage(e),
											})
										},
									}),
								)
							},
						},
					],
				},
			].filter((d) => (d.condition ? d.condition() : true))
		},
		primaryAction({ listResource: backups, documentResource: site }) {
			return {
				label: 'Take Backup',
				slots: {
					prefix: icon('upload-cloud'),
				},
				loading: site.backup.loading,
				onClick() {
					renderDialog(
						h(
							defineAsyncComponent(
								() => import('../../components/site/SiteScheduleBackup.vue'),
							),
							{
								site: site.name,
								onScheduleBackupSuccess: () => backups.reload(),
							},
						),
					)
				},
			}
		},
		banner({ documentResource: site, listResource: backups }) {
			if (site.doc?.status === 'Archived') {
				if (backups?.data && backups.data.length > 0) {
					return {
						title: 'Need help with restoring your archived site.',
						dismissable: true,
						id: site.doc.name,
						type: 'gray',
						button: {
							label: 'Contact Support',
							variant: 'outline',
							onClick() {
								window.open('https://frappecloud.com/support', '_blank')
							},
						},
					}
				}
				return
			}

			return getUpsellBanner(
				site,
				'Your site is currently on a shared bench. Upgrade plan for offsite backups and <a href="https://frappecloud.com/shared-hosting#benches" class="underline" target="_blank">more</a>.',
			)
		},
	}
}
