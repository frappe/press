<script setup lang="ts">
import { createListResource, createResource, Dialog } from 'frappe-ui'
import { computed, defineAsyncComponent, h, ref } from 'vue'
import { toast } from 'vue-sonner'
import { getTeam } from '../data/team'
import { confirmDialog, renderDialog } from '../utils/components'
import { getDocResource } from '../utils/resource'
import { getToastErrorMessage } from '../utils/toast'
import SSHCertificateDialog from './group/SSHCertificateDialog.vue'
import ActionButton from './ActionButton.vue'
import ObjectList from './ObjectList.vue'

type BenchRow = { name: string; status: string; [key: string]: any }

const props = defineProps<{
	bench: string
	releaseGroup: string
	benchRow?: BenchRow
	actionsAccess?: Record<string, boolean>
}>()

const BenchLogsDialog = defineAsyncComponent(
	() => import('./group/BenchLogsDialog.vue'),
)
const SupervisorProcessesDialog = defineAsyncComponent(
	() => import('./group/SupervisorProcessesDialog.vue'),
)

const team = getTeam()
const group = getDocResource({
	doctype: 'Release Group',
	name: props.releaseGroup,
})
const fetchedBench = createListResource({
	doctype: 'Bench',
	filters: { name: props.bench },
	fields: ['name', 'status'],
	pageLength: 1,
	auto: !props.benchRow,
})

const showAppVersionDialog = ref(false)
const appVersions = ref<any>(null)

const row = computed<BenchRow | undefined>(
	() => props.benchRow ?? fetchedBench.data?.[0],
)
const isActive = computed(() => row.value?.status === 'Active')
const supportsRebuild = computed(() => {
	const version = group.doc?.version
	if (!version) return false
	return version === 'Nightly' || Number(version.split(' ')[1]) > 13
})

const runBenchMethod = (method: string) => {
	return createResource({ url: 'press.api.client.run_doc_method' }).submit({
		dt: 'Bench',
		dn: props.bench,
		method,
	})
}

const confirmBenchMethod = (options: {
	title: string
	message: string
	label: string
	theme: string
	method: string
	success: string
}) => {
	confirmDialog({
		title: options.title,
		message: options.message,
		primaryAction: {
			label: options.label,
			variant: 'solid',
			theme: options.theme,
			onClick: ({ hide }) => {
				toast.promise(runBenchMethod(options.method), {
					loading: `${options.title}...`,
					success: () => {
						hide()
						return options.success
					},
					error: (e: unknown) => {
						hide()
						return getToastErrorMessage(e, `Failed to ${options.title}`)
					},
					duration: 1000,
				})
			},
		},
	})
}

const showApps = () => {
	const versions = createResource({ url: 'press.api.client.run_doc_method' })
	toast.promise(
		versions
			.submit({
				dt: 'Release Group',
				dn: props.releaseGroup,
				method: 'get_app_versions',
				args: { bench: props.bench },
			})
			.then((data: unknown) => {
				appVersions.value = data
				showAppVersionDialog.value = true
			}),
		{
			loading: 'Fetching apps...',
			success: 'Fetched apps with versions',
			error: 'Failed to fetch apps',
			duration: 1000,
		},
	)
}

const options = computed(() => {
	if (!row.value) return []

	return [
		{
			label: 'View in Desk',
			condition: () => team?.doc?.is_desk_user,
			onClick: () =>
				window.open(
					`${window.location.protocol}//${window.location.host}/app/bench/${props.bench}`,
					'_blank',
				),
		},
		{
			label: 'Show Apps',
			condition: () => isActive.value,
			onClick: showApps,
		},
		{
			label: 'SSH Access',
			condition: () => isActive.value,
			onClick: () =>
				renderDialog(
					h(SSHCertificateDialog, {
						bench: props.bench,
						releaseGroup: props.releaseGroup,
					}),
				),
		},
		{
			label: 'View Logs',
			condition: () => isActive.value,
			onClick: () => renderDialog(h(BenchLogsDialog, { bench: props.bench })),
		},
		{
			label: 'Update All Sites',
			condition: () => isActive.value && row.value?.site_count > 0,
			onClick: () =>
				confirmBenchMethod({
					title: 'Update All Sites',
					message: `Are you sure you want to update all sites in the bench <b>${props.bench}</b> to the latest bench?`,
					label: 'Update',
					theme: 'gray',
					method: 'update_all_sites',
					success: 'Sites have been scheduled for update',
				}),
		},
		{
			label: 'Restart Bench',
			condition: () => isActive.value,
			onClick: () =>
				confirmBenchMethod({
					title: 'Restart Bench',
					message: `Are you sure you want to restart the bench <b>${props.bench}</b>?`,
					label: 'Restart',
					theme: 'red',
					method: 'restart',
					success: 'Bench will restart shortly',
				}),
		},
		{
			label: 'Rebuild Assets',
			condition: () =>
				isActive.value && !row.value?.on_public_server && supportsRebuild.value,
			onClick: () =>
				confirmBenchMethod({
					title: 'Rebuild Assets',
					message: `Are you sure you want to rebuild assets for the bench <b>${props.bench}</b>?`,
					label: 'Rebuild',
					theme: 'red',
					method: 'rebuild',
					success:
						'Assets will be rebuilt in the background. This may take a few minutes.',
				}),
		},
		{
			label: 'Archive Bench',
			condition: () => true,
			onClick: () =>
				confirmBenchMethod({
					title: 'Archive Bench',
					message: `Are you sure you want to archive the bench <b>${props.bench}</b>?`,
					label: 'Archive',
					theme: 'red',
					method: 'archive',
					success: 'Bench is scheduled for archival',
				}),
		},
		{
			label: 'View Processes',
			condition: () => isActive.value,
			onClick: () =>
				renderDialog(h(SupervisorProcessesDialog, { bench: props.bench })),
		},
	].filter((option) => option.condition())
})

const appVersionOptions = computed(() => ({
	columns: [
		{ label: 'App', fieldname: 'app' },
		{
			label: 'Repo',
			fieldname: 'repository',
			format: (value: string, row: any) =>
				`${row.repository_owner}/${row.repository}`,
			link: (value: string, row: any) => row.repository_url,
		},
		{ label: 'Branch', fieldname: 'branch', type: 'Badge' },
		{
			label: 'Commit',
			fieldname: 'hash',
			type: 'Badge',
			format: (value: string) => value.slice(0, 7),
			link: (value: string, row: any) =>
				`https://github.com/${row.repository_owner}/${row.repository}/commit/${value}`,
		},
		{ label: 'Tag', fieldname: 'tag', type: 'Badge' },
	],
	data: () => appVersions.value,
}))
</script>

<template>
	<div>
		<ActionButton :options="options" :actionsAccess="actionsAccess" />
		<Dialog
			v-model="showAppVersionDialog"
			:options="{ title: `Apps in ${bench}`, size: '6xl' }"
		>
			<template #body-content>
				<ObjectList :options="appVersionOptions" />
			</template>
		</Dialog>
	</div>
</template>
