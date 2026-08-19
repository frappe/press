import { createResource } from 'frappe-ui'
import { defineAsyncComponent, h } from 'vue'
import { toast } from 'vue-sonner'
import BenchAppVersionsDialog from '../components/group/BenchAppVersionsDialog.vue'
import SSHCertificateDialog from '../components/group/SSHCertificateDialog.vue'
import { getTeam } from '../data/team'
import { confirmDialog, renderDialog } from './components'
import { getToastErrorMessage } from './toast'

export type BenchRow = {
	name: string
	status: string
	[key: string]: any
}

type BenchOptionsContext = {
	row: BenchRow
	releaseGroup: string
	version?: string
	actionsAccess?: Record<string, boolean>
}

export const showBenchLogs = (bench: string, initialLog?: string) => {
	const BenchLogsDialog = defineAsyncComponent(
		() => import('../components/group/BenchLogsDialog.vue'),
	)

	renderDialog(h(BenchLogsDialog, { bench, initialLog }))
}

const showProcesses = (bench: string) => {
	const SupervisorProcessesDialog = defineAsyncComponent(
		() => import('../components/group/SupervisorProcessesDialog.vue'),
	)

	renderDialog(h(SupervisorProcessesDialog, { bench }))
}

const runBenchMethod = (bench: string, method: string) =>
	createResource({ url: 'press.api.client.run_doc_method' }).submit({
		dt: 'Bench',
		dn: bench,
		method,
	})

const confirmBenchMethod = (options: {
	bench: string
	title: string
	message: string
	label: string
	theme: string
	method: string
	loading: string
	success: string
	error: string
}) => {
	confirmDialog({
		title: options.title,
		message: options.message,
		primaryAction: {
			label: options.label,
			variant: 'solid',
			theme: options.theme,
			onClick: ({ hide }) => {
				toast.promise(runBenchMethod(options.bench, options.method), {
					loading: options.loading,
					success: () => {
						hide()
						return options.success
					},
					error: (e: unknown) => {
						hide()
						return getToastErrorMessage(e, options.error)
					},
					duration: 1000,
				})
			},
		},
	})
}

const supportsRebuild = (version?: string) => {
	if (!version) return false
	return version === 'Nightly' || Number(version.split(' ')[1]) > 13
}

export const getBenchOptions = ({
	row,
	releaseGroup,
	version,
	actionsAccess,
}: BenchOptionsContext) => {
	if (!row) return []

	const bench = row.name
	const isActive = row.status === 'Active'

	return [
		{
			label: 'View in Desk',
			condition: () => getTeam()?.doc?.is_desk_user,
			onClick: () =>
				window.open(
					`${window.location.protocol}//${window.location.host}/app/bench/${bench}`,
					'_blank',
				),
		},
		{
			label: 'Show Apps',
			condition: () => isActive,
			onClick: () =>
				renderDialog(h(BenchAppVersionsDialog, { bench, releaseGroup })),
		},
		{
			label: 'SSH Access',
			condition: () => isActive,
			onClick: () => renderDialog(h(SSHCertificateDialog, { bench, releaseGroup })),
		},
		{
			label: 'View Logs',
			condition: () => isActive,
			onClick: () => showBenchLogs(bench),
		},
		{
			label: 'Update All Sites',
			condition: () => isActive && (row.rows?.length ?? row.site_count) > 0,
			onClick: () =>
				confirmBenchMethod({
					bench,
					title: 'Update All Sites',
					message: `Are you sure you want to update all sites in the bench <b>${bench}</b> to the latest bench?`,
					label: 'Update',
					theme: 'gray',
					method: 'update_all_sites',
					loading: 'Scheduling updates for the sites...',
					success: 'Sites have been scheduled for update',
					error: 'Failed to update sites',
				}),
		},
		{
			label: 'Restart Bench',
			condition: () => isActive,
			onClick: () =>
				confirmBenchMethod({
					bench,
					title: 'Restart Bench',
					message: `Are you sure you want to restart the bench <b>${bench}</b>?`,
					label: 'Restart',
					theme: 'red',
					method: 'restart',
					loading: 'Restarting bench...',
					success: 'Bench will restart shortly',
					error: 'Failed to restart bench',
				}),
		},
		{
			label: 'Rebuild Assets',
			condition: () =>
				isActive && !row.on_public_server && supportsRebuild(version),
			onClick: () =>
				confirmBenchMethod({
					bench,
					title: 'Rebuild Assets',
					message: `Are you sure you want to rebuild assets for the bench <b>${bench}</b>?`,
					label: 'Rebuild',
					theme: 'red',
					method: 'rebuild',
					loading: 'Rebuilding assets...',
					success:
						'Assets will be rebuilt in the background. This may take a few minutes.',
					error: 'Failed to rebuild assets',
				}),
		},
		{
			label: 'Archive Bench',
			condition: () => true,
			onClick: () =>
				confirmBenchMethod({
					bench,
					title: 'Archive Bench',
					message: `Are you sure you want to archive the bench <b>${bench}</b>?`,
					label: 'Archive',
					theme: 'red',
					method: 'archive',
					loading: 'Scheduling bench for archival...',
					success: 'Bench is scheduled for archival',
					error: 'Failed to archive bench',
				}),
		},
		{
			label: 'View Processes',
			condition: () => isActive,
			onClick: () => showProcesses(bench),
		},
	].filter((option) => {
		if (!(actionsAccess?.[option.label] ?? true)) return false
		return option.condition()
	})
}
