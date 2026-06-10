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
	fields: ['name', 'title', 'version'],
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
			<ServerIcon :provider="data.provider" class="size-8" />

			<div class="flex flex-wrap gap-2 items-center text-sm">
				<span>{{ data?.title }}</span>
				<div
					class="rounded-full size-2 mx-1"
					:class="data.status === 'Active' ? 'bg-surface-green-3' : 'bg-surface-red-5'"
				/>
				<span>{{ data.status }}</span>
				<span class="w-full text-ink-gray-6">
					{{ data.vcpu }}
					vCPU, {{ Math.round(data.memory / 1024) }} GB RAM,
					{{ data.disk }}
					GB Disk
				</span>
			</div>

			<div class="flex items-center gap-1 text-ink-gray-6 ml-auto">
				<LucideMapPin class="size-4" />
				<span>{{ data?.cluster_title }}</span>
				<Dropdown :options="serverActions(data)">
					<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
				</Dropdown>
			</div>
		</div>

		<!-- benches header -->
		<div
			class="row-grid pl-6 pr-4 pt-4 items-center text-ink-gray-4 text-sm"
		>
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
