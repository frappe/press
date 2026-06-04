<script setup lang="ts">
import { ref, reactive, watch, h } from 'vue'

import {
	Button,
	Tooltip,
	Spinner,
	Dropdown,
	createListResource,
} from 'frappe-ui'

import HetnzerLogo from '@/logo/Hetzner.vue'
import FrappeLogo from '@/logo/Frappe.vue'
import AwsLogo from '@/logo/Aws.vue'
import OracleLogo from '@/logo/Oracle.vue'
import DigitalOceanLogo from '@/logo/DigitalOcean.vue'

import AddBenchDialog from './AddBenchDialog.vue'
import MarketPlaceAppsDialog from './AppsDialog.vue'


import { renderDialog } from '@/utils/components'

import { dayjsLocal } from '@/utils/dayjs'
import Collapsable from '@/components/common/Collapsable.vue'

interface Props {
	data: any
}

const props = defineProps<Props>()

const sitesRes = reactive({})

const makeSiteRes = (ids: string[]) => {
	ids.forEach((id) => {
		if (sitesRes[id]) return

		sitesRes[id] = createListResource({
			doctype: 'Site',
			fields: ['name', 'status', 'bench', 'creation', 'host_name'],
			filters: { group: id },
			orderBy: 'creation desc',
			pageLength: 5,
			cache: ['sitesRes', id],
		})
	})
}
const benches = createListResource({
	doctype: 'Release Group',
	pageLength: 5,
	auto: true,
	fields: ['name', 'title', 'version'],
	makeParams() {
		return {
			filters: { server: props.data.name },
			cache: ['benchesRes', props.data.name],
		}
	},

	orderBy: 'creation desc',
	onSuccess(data) {
		makeSiteRes(data.map((x) => x.name))
	},
})

const providerIcons = {
	'Frappe Compute': FrappeLogo,
	Generic: FrappeLogo,
	Hetzner: HetnzerLogo,
	'AWS EC2': AwsLogo,
	Oracle: OracleLogo,
	DigitalOcean: DigitalOceanLogo,
}

const statusColors = {
	Active: 'bg-surface-green-3',
	Broken: 'bg-surface-red-3',
	Draft: 'bg-surface-orange-3',
	AwaitingApproval: 'bg-surface-orange-3',
}

const serverActions = (server) => {
	return [
		{
			label: 'Add bench',
			icon: LucideCirclePlus,
			onClick: () => {
				renderDialog(
					h(AddBenchDialog, {
						cluster: server.cluster,
						server: server.name,
						// onSuccess: () => servers.reload(),
					}),
				)
			},
		},
		{
			label: 'Visit server',
			icon: 'external-link',
		},
		{
			label: 'View backups',
			icon: 'archive',
		},

		{
			label: 'Change App server plan',
			icon: LucideArrowLeftRight,
		},

		{
			label: 'Change DB server plan',
			icon: LucideArrowLeftRight,
		},

		{
			label: 'Drop server',
			theme: 'red',
			icon: 'trash-2',
		},
	]
}

const deployBench = (e) => {
	e.stopPropagation()

	renderDialog(h(MarketPlaceAppsDialog))
}
</script>

<template>
	<section class="shadow dark:bg-surface-cards rounded" :key="data.name">
		<!-- header -->
		<div class="bordered p-4 flex gap-3 items-center">
			<component :is="providerIcons[data?.provider]" class="size-8" />

			<div class="flex flex-wrap gap-2 items-center text-sm">
				<span>{{ data?.title }}</span>
				<div class="rounded-full size-2 bg-surface-green-3" />
				<span>Active</span>
				<span class="w-full text-ink-gray-6">2 vCPU, 8GB RAM, 160 Disk</span>
			</div>

			<div class="flex items-center gap-1 text-ink-gray-6 ml-auto">
				<LucideMapPin class="size-4" />
				<span>{{ data?.cluster_title }}</span>

				<Dropdown :options="serverActions(data)">
					<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
				</Dropdown>
			</div>
		</div>

		<!-- bench column headers -->
		<div
			class="grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] pl-6 pr-4 pt-4 pb-0 items-center text-ink-gray-4 text-sm"
		>
			<span />
			<template v-if="benches?.data?.length">
				<span>Bench</span>
				<span>Status</span>
				<span>Version</span>
			</template>

			<div v-else class="flex gap-2 items-center pb-4">
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

		<Collapsable v-for="(bench, bench_i) in benches?.data" :key="bench.name">
			<template #header="{ opened, toggle }">
				<div
					class="grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] pl-6 pr-4 py-2 cursor-pointer items-center"
					:class="
							(benches?.data?.length - 1 == bench_i && opened) ||
							bench_i != benches?.data?.length - 1
								? 'bordered'
								: ''
						"
					@click="() => {
							if (!opened && !sitesRes[bench.name]?.data) sitesRes[bench.name]?.fetch()
							toggle()
						}"
				>
					<LucideChevronUp
						class="shrink-0 size-4 transition-transform duration-300"
						:class="opened ? '' : 'rotate-180'"
					/>
					<span class="flex gap-2 items-center">
						<LucideBoxes class="size-4" /> {{ bench.title }}
					</span>
					<div class="flex flex-wrap gap-2 items-center">
						<span
							class="size-2 rounded-full"
							:class="bench.active_benches ? 'bg-surface-green-3' : 'bg-surface-amber-3'"
						/>
						{{ bench.active_benches ? 'Active' : 'Awaiting Deploy' }}

						<button
							@click="deployBench"
							class="w-full self-start text-left mb-2 hover:underline"
						>
							Deploy
						</button>
					</div>
					<span>{{ bench.version }}</span>
					<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
				</div>
			</template>

			<!-- site sub-header + rows -->
			<div class="p-10 flex" v-if="sitesRes[bench.name]?.list?.loading">
				<span class="flex gap-2 items-center m-auto">
					<Spinner />
					Loading...
				</span>
			</div>

			<div
				class="grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] px-4 py-2 items-center text-sm text-ink-gray-5"
				:class='bench_i != benches?.data?.length -1 ?  "bordered" : ""'
			>
				<span />
				<span class="ml-8">Site</span>
				<span>Status</span>
				<span>Created</span>
				<span />

				<!-- site rows -->
				<template
					v-for="(site, site_i) in sitesRes[bench.name]?.data"
					:key="site.name"
				>
					<span />
					<span class="flex gap-2 items-center text-ink-gray-8 ml-8">
						<LucideAppWindow class="size-4" /> {{ site.name }}
					</span>
					<div class="flex gap-2 items-center text-ink-gray-8">
						<span
							class="size-2 rounded-full"
							:class="statusColors[site.status]"
						/>
						{{ site.status }}
					</div>
					<span class="text-ink-gray-8"
						>{{ dayjsLocal(site.creation).fromNow() }}</span
					>
					<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>

					<div
						v-if="site_i != sitesRes[bench.name]?.data?.length - 1"
						class="bordered col-span-full -mx-4"
					/>
				</template>
			</div>
		</Collapsable>
	</section>
</template>

<style scoped>
.bordered {
	@apply border-b dark:border-outline-gray-2
}
</style>
