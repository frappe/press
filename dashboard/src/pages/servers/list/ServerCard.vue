<script setup lang="ts">
import { h, defineAsyncComponent } from 'vue'
import { Button, Tooltip, Dropdown, createListResource } from 'frappe-ui'

import { renderDialog } from '@/utils/components'
import { onDropServer } from './utils'
import ServerIcon from './ServerIcon.vue'

import BenchRow from './BenchRow.vue'

interface Props {
	data: any
}

const props = defineProps<Props>()

const benches = createListResource({
	doctype: 'Release Group',
	pageLength: 5,
	auto: true,
	fields: ['name', 'title', 'version', 'active_benches', 'site_count'],
	filters: { server: props.data.name },
	cache: ['benchesRes', props.data.name],
	orderBy: 'creation desc',
})

const serverActions = (server) => [
	{
		label: 'Add bench',
		icon: LucideCirclePlus,
		onClick: () => {
			const AddBenchDialog = defineAsyncComponent(
				() => import('./AddBenchDialog.vue'),
			)
			renderDialog(
				h(AddBenchDialog, {
					server: server,
					onSuccess: () => benches.reload(),
				}),
			)
		},
	},
	{
		label: 'Visit server',
		icon: 'external-link',
		route: `/servers/${server.name}`,
	},
	{ label: 'View backups', icon: 'archive' },
	{
		label: 'Go to Server Actions',
		icon: LucideSlidersVertical,
		route: `/servers/${server.name}/actions`,
	},
	{
		label: 'Drop server',
		theme: 'red',
		icon: 'trash-2',
		onClick: () => onDropServer(server),
	},
]
</script>

<template>
	<section class="shadow dark:bg-surface-cards rounded" :key="data.name">
		<div class="bordered p-4 flex gap-3 items-center">
			<ServerIcon :provider="data.provider" class="size-6 mb-auto" />

			<div class="flex flex-wrap gap-1.5 items-center">
				<Tooltip text="Go to server dashboard">
					<router-link :to="`/servers/${data.name}`" class="hover:underline">
						<span class="font-medium">{{ data?.title }}</span>
					</router-link>
				</Tooltip>

				<div
					class="rounded-full size-1.5 ml-1"
					:class="data.status === 'Active' ? 'bg-surface-green-3' : 'bg-surface-red-5'"
				/>
				<span class='text-xs'>{{ data.status }}</span>
				<span class="w-full text-ink-gray-6 text-sm">
					{{ data.vcpu }}
					vCPU, {{ Math.round(data.memory / 1024) }} GB RAM,
					{{ data.disk }}
					GB Disk
				</span>
			</div>

			<div class="flex items-center gap-1 text-ink-gray-6 ml-auto">
				<img
					v-if="data?.cluster_image"
					:src="data.cluster_image"
					:alt="data?.cluster_title"
					class="size-4 mr-1"
				/>
				<LucideMapPin v-else class="size-4" />
				<span>{{ data?.cluster_title }}{{ data?.cluster_country ? `, ${data.cluster_country}` : '' }}</span>
				<Dropdown :options="serverActions(data)">
					<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
				</Dropdown>
			</div>
		</div>

		<!-- benches header -->
		<div class="row-grid pl-6 pr-4 pt-4 items-center text-ink-gray-5 text-sm">
			<span />
			<template v-if="benches?.data?.length">
				<span>Bench</span>
				<span>Status</span>
				<span>Version</span>
			</template>

			<div v-else class="flex gap-2 items-center pb-2 col-span-4">
				<Tooltip
					text="Add benches via the more button or benches tab to start hosting sites"
					:hoverDelay="0"
				>
					<LucideAlertCircle class="size-4" />
				</Tooltip>
				<span class="text-ink-gray-5">No Benches added</span>
			</div>
			<span />
		</div>

		<BenchRow
			v-for="(bench, bench_i) in benches?.data"
			:key="bench.name"
			:bench_i="bench_i"
			:data="bench"
			:totalLength="benches?.data?.length"
			:server="data"
		/>

		<div v-if="benches.hasNextPage" class="px-6 py-2 border-t dark:border-outline-gray-2">
			<Button variant="ghost" @click="benches.next()" :loading="benches.list?.loading">
				Load more
			</Button>
		</div>
	</section>
</template>

<style scoped>
.bordered {
	@apply border-b dark:border-outline-gray-2;
}

.row-grid {
	@apply grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem];
}
</style>
