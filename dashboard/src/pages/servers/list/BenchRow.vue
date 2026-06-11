<script setup lang="ts">
import {
	Button,
	Dropdown,
	Spinner,
	Tooltip,
	createResource,
	createDocumentResource,
	createListResource,
} from 'frappe-ui'

import { renderDialog } from '@/utils/components'
import {
	h,
	ref,
	defineAsyncComponent,
	onBeforeUnmount,
	computed,
	reactive,
	watch,
} from 'vue'
import { dropBench } from './utils'

import { dayjsLocal } from '@/utils/dayjs'
import Collapsable from '@/components/common/Collapsable.vue'

interface Props {
	data: any
	totalLength: number
	bench_i: number
	server: any
}

const socket = window.$socket
const props = defineProps<Props>()

const sites = createListResource({
	doctype: 'Site',
	fields: ['name', 'status', 'bench', 'creation', 'host_name'],
	filters: { group: props.data.name },
	orderBy: 'creation desc',
	pageLength: 5,
	cache: ['sitesRes', props.data.name],
	auto: true,
})

const wired = ref(false)
const pipelineId = ref(null)
const pipelineRes = ref()

const benchDeployStatus = computed(() => {
	if (!pipelineRes.value?.doc) return

	let status = 'Deploy in Queue'
	const stages = pipelineRes.value.doc.steps.stages
	const firstRunning = stages.find((x) => x.status === 'Running')

	if (firstRunning) status = firstRunning.label
	const firstFailure = stages.find((x) => x.status === 'Failure')
	if (firstFailure) status = 'Failed'

	if (pipelineRes.value.doc.status == 'Success')
		status = 'Deployed Successfully'

	return status
})

const handlePipelineUpdate = (x) => {
	if (x.doctype === 'Release Pipeline' && x.name === pipelineId.value) {
		pipelineRes.value.reload()
	}
}

const attachPipeline = (id: string) => {
	pipelineId.value = id
	pipelineRes.value = createDocumentResource({
		doctype: 'Release Pipeline',
		name: id,
		auto: true,
		onSuccess(data) {
			if (['Success', 'Failure'].includes(data.status)) {
				pipelineRes.value = null
				pipelineId.value = null
				wired.value = false
			} else if (!wired.value) {
				socket.emit('doc_subscribe', 'Release Pipeline', id)
				socket.on('doc_update', handlePipelineUpdate)
				wired.value = true
			}
		},
	})
}

if (!props.data.active_benches) {
	onBeforeUnmount(() => {
		if (pipelineId.value) {
			socket.emit('doc_unsubscribe', 'Release Pipeline', pipelineId.value)
			socket.off('doc_update', handlePipelineUpdate)
		}
	})
}

if (!props.data.active_benches) {
	createResource({
		url: 'frappe.client.get_value',
		params: {
			doctype: 'Release Pipeline',
			filters: {
				release_group: props.data.name,
				status: ['in', ['Running', 'Pending']],
			},
			fieldname: 'name',
		},
		auto: true,
		onSuccess(data) {
			if (!data?.name) return
			attachPipeline(data.name)
		},
	})
}

const deployBench = (e, bench, server) => {
	e.stopPropagation()
	const AppsDialog = defineAsyncComponent(() => import('./AppsDialog.vue'))
	renderDialog(
		h(AppsDialog, {
			bench,
			server,
			onDeployed: (x) => {
				attachPipeline(x)
			},
		}),
	)
}

const addSite = (e, bench) => {
	e?.stopPropagation()
	const AddSiteDialog = defineAsyncComponent(
		() => import('./AddSiteDialog.vue'),
	)
	renderDialog(h(AddSiteDialog, { bench, onSiteCreated: () => sites.reload() }))
}

const benchOptions = (bench) => [
	{
		label: 'Add Site',
		icon: 'plus-circle',
		onClick: () => addSite(null, bench),
	},
	{ label: 'App Marketplace', route: '/apps', icon: LucideStore },
	{
		label: 'Bench Actions',
		route: `/groups/${bench.name}/actions`,
		icon: LucideSlidersVertical,
	},
	{
		label: 'Drop bench',
		theme: 'red',
		variant: 'subtle',
		icon: 'trash-2',
		onClick: () => dropBench(bench),
	},
]

const statusColors = {
	Active: 'bg-surface-green-3',
	Broken: 'bg-surface-red-3',
	Draft: 'bg-surface-orange-3',
	AwaitingApproval: 'bg-surface-orange-3',
}

const transientSiteStatuses = [
	'Pending',
	'Installing',
	'Updating',
	'Recovering',
]
const wiredSites = reactive(new Set<string>())

const handleSiteUpdate = (x) => {
	if (x.doctype === 'Site' && wiredSites.has(x.name)) {
		sites.reload()
	}
}

socket.on('doc_update', handleSiteUpdate)

watch(
	() => sites.data,
	(data) => {
		data?.forEach((site) => {
			if (
				transientSiteStatuses.includes(site.status) &&
				!wiredSites.has(site.name)
			) {
				socket.emit('doc_subscribe', 'Site', site.name)
				wiredSites.add(site.name)
			}
		})
	},
	{ immediate: true },
)

onBeforeUnmount(() => {
	socket.off('doc_update', handleSiteUpdate)
	wiredSites.forEach((name) => {
		socket.emit('doc_unsubscribe', 'Site', name)
	})
})
</script>

<template>
	<Collapsable>
		<template #header="{ opened, toggle }">
			<div
				:class="[
					'row-grid pl-6 pr-4 py-2 cursor-pointer items-center',
					(totalLength - 1 == bench_i && opened) || bench_i != totalLength - 1
						? 'bordered'
						: '',
				]"
				@click="() => {
					toggle()
				}"
			>
				<LucideChevronRight
					class="shrink-0 size-4 transition-transform duration-300"
					:class="opened ? 'rotate-90' : ''"
				/>

				<Tooltip text="Go to bench dashboard">
					<router-link
						class="flex gap-2 items-center hover:underline w-fit"
						:to="`/groups/${data.name}`"
						@click.prevent="(e) => e.stopPropagation()"
					>
						<LucideBoxes class="size-4" />
						{{ data.title }}

						<span
							v-if="data.site_count"
							class="text-xs bg-surface-gray-2 text-ink-gray-6 rounded px-1.5 py-0.5 font-medium"
						>
							{{ data.site_count }}
						</span>
					</router-link>
				</Tooltip>

				<div
					class="flex flex-wrap gap-x-2.5 gap-y-1.5 items-center"
					v-if="!pipelineId"
				>
					<span
						class="size-2 rounded-full"
						:class="data.active_benches ? 'bg-surface-green-3' : 'bg-surface-amber-3'"
					/>
					{{ data.active_benches ? 'Active' : 'Awaiting Deploy' }}
					<button
						v-if="!data.active_benches"
						@click="(e) => deployBench(e, data, server)"
						class="w-full self-start text-left mb-1 ml-4 hover:underline"
					>
						Deploy
					</button>
				</div>

				<router-link
					v-else
					class="flex gap-2 items-center -ml-1"
					:to="{ name: 'Release Pipeline', params: { id: pipelineId, name: data.name } }"
					@click.prevent="(e) => e.stopPropagation()"
				>
					<Spinner />

					<template v-if="!benchDeployStatus">Deploy in queue</template>

					<template v-else>
						{{ benchDeployStatus }}
						<LucideExternalLink class="size-4" />
					</template>
				</router-link>

				<span>{{ data.version }}</span>

				<Dropdown :options="benchOptions(data)">
					<Button variant="ghost" @click="(e) => e.stopPropagation()">
						<LucideEllipsis class="size-4" />
					</Button>
				</Dropdown>
			</div>
		</template>

		<div class="p-10 flex" v-if="sites?.list?.loading">
			<span class="flex gap-2 items-center m-auto">
				<Spinner />
				Loading...
			</span>
		</div>

		<div
			v-if="sites?.data?.length > 0"
			class="row-grid px-6 pr-4 py-2 items-center text-sm text-ink-gray-5"
		>
			<span />
			<span>Site</span>
			<span>Status</span>
			<span>Modified / Created on</span>
			<span />
		</div>

		<div
			v-else-if="!sites?.list?.loading"
			class="row-grid px-6 pr-4 py-2"
			:class="[bench_i != totalLength - 1 ? 'bordered' : '']"
		>
			<span />
			<Button
				class="w-fit ml-3"
				variant="ghost"
				@click="(e) => addSite(e, data)"
			>
				<template #prefix>
					<LucidePlus class="size-4" />
				</template>
				Add site
			</Button>
		</div>

		<div
			v-for="(site, site_i) in sites?.data"
			:key="site.name"
			:class="[
				'row-grid px-6 pr-4 py-2 items-center',
				site_i != sites?.data?.length - 1 || bench_i != totalLength - 1
					? 'bordered'
					: '',
			]"
		>
			<span />

			<Tooltip text="Go to site dashboard">
				<router-link
					class="flex gap-2 w-fit items-center hover:underline text-ink-gray-8 pl-4"
					:to="`/sites/${site.name}`"
				>
					<LucideAppWindow class="size-4" /> {{ site.name }}
				</router-link>
			</Tooltip>

			<router-link
				v-if="['Pending', 'Installing', 'Updating', 'Recovering'].includes(site.status)"
				:to="`/sites/${site.name}`"
				class="flex gap-2 items-center text-ink-gray-8"
			>
				<Spinner />
				{{ site.status }}
				<LucideExternalLink class="size-4" />
			</router-link>

			<div v-else class="flex gap-2 items-center text-ink-gray-8">
				<span class="size-2 rounded-full" :class="statusColors[site.status]" />
				{{ site.status }}
			</div>

			<span class="text-ink-gray-8"
				>{{ dayjsLocal(site.creation).fromNow() }}</span
			>
			<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
		</div>
	</Collapsable>
</template>

<style scoped>
.bordered {
	@apply border-b dark:border-outline-gray-2;
}

.row-grid {
	@apply grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem];
}
</style>
