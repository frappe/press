<script setup lang="ts">
import {
	Badge,
	Button,
	Dropdown,
	Spinner,
	Tooltip,
	createListResource,
	createDocumentResource,
} from 'frappe-ui'
import { h, ref, computed, defineAsyncComponent, onBeforeUnmount, watch, reactive } from 'vue'
import Collapsable from '@/components/common/Collapsable.vue'
import { renderDialog } from '@/utils/components'
import { dropBench } from '@/pages/servers/list/utils'

interface Props {
	data: any
	isLast: boolean
}

const props = defineProps<Props>()
const socket = window.$socket

const sites = createListResource({
	doctype: 'Site',
	fields: [
		'name',
		'status',
		'host_name',
		'server',
		'cluster.title as cluster_title',
		'cluster.country as cluster_country',
		'cluster.image as cluster_image',
	],
	filters: {
		group: props.data.name,
		host_name: ['is', 'set'],
		skip_team_filter_for_system_user_and_support_agent: true,
	},
	orderBy: 'creation desc',
	pageLength: 5,
	auto: false,
})

function onToggle(toggle: () => void) {
	toggle()
	if (!sites.data && props.data.site_count) sites.reload()
}


const pipelineId = ref<string | null>(null)
const pipelineRes = ref<any>(null)
const wired = ref(false)

const benchDeployStatus = computed(() =>
	pipelineRes.value?.doc ? 'Deploying' : null,
)

const handlePipelineUpdate = (x: any) => {
	if (x.doctype === 'Release Pipeline' && x.name === pipelineId.value) {
		pipelineRes.value.reload()
	}
}

function attachPipeline(id: string) {
	pipelineId.value = id
	pipelineRes.value = createDocumentResource({
		doctype: 'Release Pipeline',
		name: id,
		auto: true,
		onSuccess(data: any) {
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
		onSuccess(data: any) {
			if (data?.[0]?.name) attachPipeline(data[0].name)
		},
	})
}

onBeforeUnmount(() => {
	if (pipelineId.value) {
		socket.emit('doc_unsubscribe', 'Release Pipeline', pipelineId.value)
		socket.off('doc_update', handlePipelineUpdate)
	}
	socket.off('doc_update', handleSiteUpdate)
	wiredSites.forEach((name) => socket.emit('doc_unsubscribe', 'Site', name))
})


const transientStatuses = ['Pending', 'Installing', 'Updating', 'Recovering']
const wiredSites = reactive(new Set<string>())

const handleSiteUpdate = (x: any) => {
	if (x.doctype === 'Site' && wiredSites.has(x.name)) sites.reload()
}

socket.on('doc_update', handleSiteUpdate)

watch(
	() => sites.data,
	(data) => {
		data?.forEach((site: any) => {
			if (transientStatuses.includes(site.status) && !wiredSites.has(site.name)) {
				socket.emit('doc_subscribe', 'Site', site.name)
				wiredSites.add(site.name)
			}
		})
	},
	{ immediate: true },
)


function openDeployDialog(e: Event) {
	e.stopPropagation()
	const AppsDialog = defineAsyncComponent(
		() => import('@/pages/servers/list/AppsDialog.vue'),
	)
	const server = {
		name: props.data.server,
		title: props.data.server_title,
		provider: props.data.server_provider,
	}
	renderDialog(
		h(AppsDialog, {
			bench: props.data,
			server,
			onDeployed: (pipelineId: string) => attachPipeline(pipelineId),
		}),
	)
}

function openAddSiteDialog() {
	const AddSiteDialog = defineAsyncComponent(
		() => import('@/pages/servers/list/AddSiteDialog.vue'),
	)
	renderDialog(h(AddSiteDialog, { bench: props.data, onSiteCreated: () => sites.reload() }))
}

const groupOptions = [
	{
		label: 'Add Site',
		icon: 'plus-circle',
		onClick: openAddSiteDialog,
	},
	{ label: 'App Marketplace', route: '/apps', icon: LucideStore },
	{
		label: 'Bench Actions',
		route: { name: 'Release Group Detail Actions', params: { name: props.data.name } },
		icon: LucideSlidersVertical,
	},
	{
		label: 'Drop bench',
		theme: 'red',
		variant: 'subtle',
		icon: 'trash-2',
		onClick: () => dropBench(props.data),
	},
]

const siteOptions = (site: any) => [
	{
		label: 'Site Actions',
		route: { name: 'Site Detail Actions', params: { name: site.name } },
		icon: LucideSlidersVertical,
	},
]

const siteStatusBadges: Record<string, { theme: 'green' | 'red' | 'orange' | 'blue' | 'gray' | null; dot: string }> = {
	Active: { theme: null, dot: 'bg-surface-green-3' },
	Inactive: { theme: 'gray', dot: 'bg-surface-gray-4' },
	Suspended: { theme: 'gray', dot: 'bg-surface-gray-4' },
	Archived: { theme: 'gray', dot: 'bg-surface-gray-4' },
	Broken: { theme: 'red', dot: 'bg-surface-red-5' },
	Draft: { theme: 'orange', dot: 'bg-surface-orange-3' },
	AwaitingApproval: { theme: 'orange', dot: 'bg-surface-orange-3' },
	'Update Available': { theme: 'blue', dot: 'bg-surface-blue-3' },
}
const defaultSiteStatusBadge = { theme: 'gray' as const, dot: 'bg-surface-gray-4' }
</script>

<template>
	<Collapsable>
		<template #header="{ opened, toggle }">
			<div
				class="bench-grid px-2 py-1.5 cursor-pointer items-center"
				:class="opened || !isLast ? 'border-b dark:border-outline-gray-2' : ''"
				@click="onToggle(toggle)"
			>
				<LucideChevronRight
					class="shrink-0 size-4 transition-transform duration-300 text-ink-gray-5"
					:class="opened ? 'rotate-90' : ''"
				/>

				<div class="flex gap-2 items-center min-w-0">
					<Tooltip text="Go to bench dashboard">
						<router-link
							class="hover:underline flex gap-2 items-center font-medium min-w-0"
							:to="{ name: 'Release Group Detail', params: { name: data.name } }"
							@click.stop
						>
							<LucideBoxes class="size-4 shrink-0 text-ink-gray-5" />
							<span class="truncate">{{ data.title }}</span>
						</router-link>
					</Tooltip>
					<Tooltip :text="`${data.site_count || 0} sites`">
						<span class="text-xs bg-surface-gray-2 text-ink-gray-6 rounded px-1.5 py-0.5 font-medium shrink-0">
							{{ data.site_count || 0 }}
						</span>
					</Tooltip>
				</div>

				<div v-if="!pipelineId" class="flex gap-2 items-center">
					<Badge
						variant="subtle"
						class="w-fit"
						:theme="data.active_benches ? null : 'orange'"
					>
						<span
							class="size-1.5 rounded-full shrink-0 mr-0.5"
							:class="data.active_benches ? 'bg-surface-green-3' : 'bg-surface-amber-3'"
						/>
						{{ data.active_benches ? 'Active' : 'Awaiting Deploy' }}
					</Badge>
					<button
						v-if="!data.active_benches"
						class="p-1 rounded-sm -ml-1 hover:bg-surface-gray-2"
						@click="openDeployDialog"
					>
						<LucideRocket class="size-3.5" />
					</button>
				</div>

				<router-link
					v-else
					class="flex gap-2 items-center text-xs"
					:to="{ name: 'Release Pipeline', params: { id: pipelineId, name: data.name } }"
					@click.stop
				>
					<Spinner class="!size-3.5" />
					<template v-if="!benchDeployStatus">Deploy in queue</template>
					<template v-else>
						{{ benchDeployStatus }}
						<LucideExternalLink class="size-3.5" />
					</template>
				</router-link>

				<span class="text-ink-gray-6 text-sm">{{ data.version }}</span>

				<span class="text-ink-gray-5 text-sm truncate">
					{{ (data.apps || []).map((a: any) => a.app).join(', ') }}
				</span>

				<Dropdown :options="groupOptions">
					<Button variant="ghost" @click.stop>
						<LucideEllipsis class="size-4" />
					</Button>
				</Dropdown>
			</div>
		</template>

		<div
			v-if="sites.list?.loading && !sites.data?.length"
			class="bench-grid px-2 py-3 items-center"
		>
			<span />
			<span class="pl-6 flex items-center gap-2 text-sm text-ink-gray-5">
				<Spinner class="size-4" />
				Loading sites
			</span>
		</div>

		<template v-else-if="sites.data?.length">
			<div class="bench-grid px-2 py-2 text-xs text-ink-gray-5 items-center">
				<span />
				<span class="pl-6">Site</span>
				<span>Status</span>
				<span>Server</span>
				<span>Region</span>
				<span />
			</div>

			<div
				v-for="(site, i) in sites.data"
				:key="site.name"
				class="bench-grid px-2 py-2 items-center fade-in"
				:class="(i < sites.data.length - 1 || sites.hasNextPage) ? 'border-b dark:border-outline-gray-2' : (!isLast ? 'border-b dark:border-outline-gray-2' : '')"
			>
				<span />

				<router-link
					class="flex gap-2 items-center hover:underline text-ink-gray-8 pl-6 min-w-0"
					:to="{ name: 'Site Detail', params: { name: site.name } }"
				>
					<LucideAppWindow class="size-4 shrink-0 text-ink-gray-5" />
					<span class="truncate">{{ site.name }}</span>
				</router-link>

				<router-link
					v-if="transientStatuses.includes(site.status)"
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
					:theme="(siteStatusBadges[site.status] || defaultSiteStatusBadge).theme"
				>
					<span
						class="size-1.5 rounded-full shrink-0 mr-0.5"
						:class="(siteStatusBadges[site.status] || defaultSiteStatusBadge).dot"
					/>
					{{ site.status }}
				</Badge>

				<span class="text-ink-gray-6 text-sm flex gap-1.5 items-center min-w-0">
					<LucideServer class="size-3.5 shrink-0" />
					<span class="truncate">{{ site.server || '—' }}</span>
				</span>

				<span class="text-ink-gray-6 text-sm flex gap-1.5 items-center min-w-0">
					<img v-if="site.cluster_image" :src="site.cluster_image" class="size-3.5 shrink-0" />
					<span class="truncate">{{ site.cluster_title }}{{ site.cluster_country ? `, ${site.cluster_country}` : '' }}</span>
				</span>

				<Dropdown :options="siteOptions(site)">
					<Button variant="ghost">
						<LucideEllipsis class="size-4" />
					</Button>
				</Dropdown>
			</div>

			<div
				v-if="sites.hasNextPage"
				class="px-2 py-2"
				:class="!isLast ? 'border-b dark:border-outline-gray-2' : ''"
			>
				<Button variant="ghost" :loading="sites.list?.loading" @click="sites.next()">
					Load more
				</Button>
			</div>
		</template>

		<div
			v-else-if="data.site_count === 0 || (Array.isArray(sites.data) && !sites.data.length)"
			class="bench-grid px-2 py-2 items-center"
			:class="!isLast ? 'border-b dark:border-outline-gray-2' : ''"
		>
			<span />
			<Button class="w-fit pl-3" variant="ghost" @click.stop="openAddSiteDialog">
				<template #prefix><LucidePlus class="size-4" /></template>
				Add site
			</Button>
		</div>
	</Collapsable>
</template>

<style scoped>
.bench-grid {
	@apply grid gap-3 grid-cols-[1.5rem_2fr_1fr_0.6fr_1fr_2rem];
}
</style>
