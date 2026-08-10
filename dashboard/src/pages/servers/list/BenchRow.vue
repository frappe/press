<script setup lang="ts">
import {
	Badge,
	Button,
	Dropdown,
	Spinner,
	Tooltip,
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
import { getSiteStatusBadge } from '@/utils/site'
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
	filters: {
		group: props.data.name,
		host_name: ['is', 'set'],
		skip_team_filter_for_system_user_and_support_agent: true,
	},
	orderBy: 'creation desc',
	pageLength: 5,
	cache: ['sitesRes', props.data.name],
	auto: true,
})

const wired = ref(false)
const pipelineId = ref(null)
const pipelineRes = ref()

const benchDeployStatus = computed(() =>
	!pipelineRes.value?.doc ? null : 'Deploying',
)

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
				socket.emit('doc_unsubscribe', 'Release Pipeline', id)
				socket.off('doc_update', handlePipelineUpdate)
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

onBeforeUnmount(() => {
	if (pipelineId.value) {
		socket.emit('doc_unsubscribe', 'Release Pipeline', pipelineId.value)
		socket.off('doc_update', handlePipelineUpdate)
	}
})

if (!props.data.active_benches) {
	createListResource({
		doctype: 'Release Pipeline',
		fields: ['name'],
		filters: {
			release_group: props.data.name,
			status: ['in', ['Running', 'Pending']],
		},
		pageLength: 1,
		auto: true,
		onSuccess(data) {
			if (!data?.[0]?.name) return
			attachPipeline(data[0].name)
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
		route: { name: 'Release Group Detail Actions', params: { name: bench.name } },
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

const dropSite = (site) => {
	const ArchiveSiteDialog = defineAsyncComponent(
		() => import('@/components/site/ArchiveSiteDialog.vue'),
	)
	const siteResource = createDocumentResource({
		doctype: 'Site',
		name: site.name,
		auto: true,
	})
	renderDialog(
		h(ArchiveSiteDialog, {
			site: siteResource,
			modelValue: true,
			onArchived: () => sites.reload(),
		}),
	)
}

const siteOptions = (site) => [
	{
		label: 'Site Actions',
		route: { name: 'Site Detail Actions', params: { name: site.name } },
		icon: LucideSlidersVertical,
	},
	{
		label: 'Drop site',
		theme: 'red',
		variant: 'subtle',
		icon: 'trash-2',
		onClick: () => dropSite(site),
	},
]

const transientStatuses = ['Pending', 'Installing', 'Updating', 'Recovering']
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
				transientStatuses.includes(site.status) &&
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
	wiredSites.forEach((name) => socket.emit('doc_unsubscribe', 'Site', name))
})
</script>

<template>
	<Collapsable>
		<template #header="{ opened, toggle }">
			<div
				:class="[
					'row-grid px-4 py-2 cursor-pointer items-center',
					(totalLength - 1 == bench_i && opened) || bench_i != totalLength - 1
						? 'bordered'
						: '',
				]"
				@click="() => {
					toggle()
				}"
			>
				<LucideChevronRight
					class="shrink-0 size-4 justify-self-end transition-transform duration-300"
					:class="opened ? 'rotate-90' : ''"
				/>

				<div class="flex gap-2 items-center w-fit">
					<Tooltip text="Go to bench dashboard">
						<router-link
							class="hover:underline flex gap-2"
							:to="{ name: 'Release Group Detail', params: { name: data.name } }"
							@click.prevent="(e) => e.stopPropagation()"
						>
							<LucideBoxes class="size-4" />
							{{ data.title }}
						</router-link>
					</Tooltip>

					<Tooltip :text="`${data.site_count || 0} sites`">
						<span
							class="text-xs bg-surface-gray-2 text-ink-gray-6 rounded px-1.5 py-0.5 font-medium"
						>
							{{ data.site_count || 0 }}
						</span>
					</Tooltip>
				</div>

				<div
					class="flex flex-wrap gap-x-2.5 gap-y-1.5 items-center"
					v-if="!pipelineId"
				>
					<Badge
						variant="subtle"
						:theme='data.active_benches? null : "orange" '
					>
						<span
							class="size-1.5 rounded-full shrink-0 mr-0.5"
							:class="data.active_benches ? 'bg-surface-green-3' : 'bg-surface-amber-3'"
						/>
						{{ data.active_benches ? 'Active' : 'Awaiting Deploy' }}
					</Badge>

					<button
						v-if="!data.active_benches"
						@click="(e) => deployBench(e, data, server)"
						class="p-1 rounded-sm -ml-1 hover:bg-surface-gray-2"
					>
						<LucideRocket class="size-3.5" />
					</button>
				</div>

				<router-link
					v-else
					class="flex gap-2 items-center ml-0.5 text-xs"
					:to="{ name: 'Release Pipeline', params: { id: pipelineId, name: data.name } }"
					@click.prevent="(e) => e.stopPropagation()"
				>
					<Spinner class="!size-3.5" />

					<template v-if="!benchDeployStatus">Deploy in queue</template>

					<template v-else>
						{{ benchDeployStatus }}
						<LucideExternalLink class="size-3.5" />
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

		<div class="p-10 flex" v-if="sites?.list?.loading && !sites?.data?.length">
			<span class="flex gap-2 items-center m-auto">
				<Spinner />
				Loading...
			</span>
		</div>

		<div
			v-if="sites?.data?.length > 0"
			class="row-grid px-4 py-2 items-center text-sm text-ink-gray-5"
		>
			<span />
			<span class="ml-6">Site</span>
			<span>Status</span>
			<span>Modified / Created on</span>
			<span />
		</div>

		<div
			v-else-if="!sites?.list?.loading"
			class="row-grid px-4 py-2"
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
				'row-grid px-4 py-2 items-center',
				site_i != sites?.data?.length - 1 || bench_i != totalLength - 1
					? 'bordered'
					: '',
			]"
		>
			<span />

			<Tooltip text="Go to site dashboard">
				<router-link
					class="flex gap-2 w-fit items-center hover:underline text-ink-gray-8 pl-6"
					:to="{ name: 'Site Detail', params: { name: site.name } }"
				>
					<LucideAppWindow class="size-4" /> {{ site.name }}
				</router-link>
			</Tooltip>

			<router-link
				v-if="['Pending', 'Installing', 'Updating', 'Recovering'].includes(site.status)"
				:to="{ name: 'Site Detail', params: { name: site.name } }"
				class="flex gap-2 items-center text-xs text-ink-gray-8"
			>
				<Spinner class="!size-3.5" />
				{{ site.status }}
				<LucideExternalLink class="size-3.5" />
			</router-link>

			<Badge
				v-else
				variant="subtle"
				class="w-fit"
				:theme="getSiteStatusBadge(site.status).theme"
			>
				<span
					class="size-1.5 rounded-full shrink-0 mr-0.5"
					:class="getSiteStatusBadge(site.status).dot"
				/>
				{{ site.status }}
			</Badge>

			<span class="text-ink-gray-8"
				>{{ dayjsLocal(site.creation).fromNow() }}</span
			>
			<Dropdown :options="siteOptions(site)">
				<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
			</Dropdown>
		</div>

		<div
			v-if="sites.hasNextPage"
			class="px-4 py-2 border-t dark:border-outline-gray-2"
		>
			<Button
				variant="ghost"
				@click="sites.next()"
				:loading="sites.list?.loading"
			>
				Load more
			</Button>
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
