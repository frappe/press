<script setup lang="ts">
import { Button, createListResource, TextInput, Select } from 'frappe-ui'
import Header from '@/components/Header.vue'
import { ref, reactive, watch } from 'vue'
import { dayjsLocal } from '@/utils/dayjs'
import Collapsable from '@/components/common/Collapsable.vue'

import HetnzerLogo from '@/logo/Hetzner.vue'
import FrappeLogo from '@/logo/Frappe.vue'
import AwsLogo from '@/logo/Aws.vue'
import OracleLogo from '@/logo/Oracle.vue'

const searchQuery = ref('')
const benchesRes = reactive({})
const sitesRes = reactive({})
const sortBy = ref('desc')

const makeSiteRes = (ids: string[]) => {
	ids.forEach((id) => {
		sitesRes[id] = createListResource({
			doctype: 'Site',
			fields: ['name', 'status', 'bench', 'creation', 'host_name'],
			filters: { group: id },
			orderBy: 'creation desc',
			pageLength: 5,
		})
	})
}

const makeBenchesRes = (ids: string[]) => {
	ids.forEach((id) => {
		benchesRes[id] = createListResource({
			doctype: 'Release Group',
			pageLength: 5,
			auto: true,
			fields: ['name', 'title', 'version'],
			filters: { server: id },
			orderBy: 'creation desc',
			onSuccess(data) {
				makeSiteRes(data.map((x) => x.name))
			},
		})
	})
}

const servers = createListResource({
	doctype: 'Server',
	auto: true,
	fields: [
		'name',
		'title',
		'provider',
		'database_server',
		'plan.title as plan_title',
		'plan.price_usd as price_usd',
		'plan.price_inr as price_inr',
		'cluster.image as cluster_image',
		'cluster.title as cluster_title',
		'is_unified_server',
	],
	orderBy: `creation ${sortBy}`,
	onSuccess(data) {
		const serverIds = data.map((x) => x.name)
		makeBenchesRes(serverIds)
	},
})

watch(searchQuery, (value) => {
	servers.update({
		filters: value ? { title: ['like', `%${value.toLowerCase()}%`] } : {},
		start: 0,
		pageLength: 20,
	})
	servers.reload()
})

const regions = [
	'',
	'Bahrain',
	'Cape Town',
	'Frankfurt',
	'KSA',
	'London',
	'Mumbai',
	'Singapore',
	'UAE',
	'Virginia',
	'Zurich',
]

const applyFilters = (key: string, value: string) => {
	servers.update({
		filters: { ...servers.filters, [key]: value || undefined },
		start: 0,
		pageLength: 20,
	})
	servers.reload()
}

const toggleSort = () => {
	sortBy.value = sortBy.value === 'desc' ? 'asc' : 'desc'
	servers.update({ orderBy: `creation ${sortBy.value}` })
	servers.reload()
}

const providerIcons = {
	'Frappe Compute': FrappeLogo,
	Generic: FrappeLogo,
	Hetzner: HetnzerLogo,
	'AWS EC2': AwsLogo,
	Oracle: OracleLogo,
}
</script>

<template>
	<Header class="sticky top-0 z-10 bg-surface-white mb-5">
		<Breadcrumbs :items="[{ label: 'Servers', route: '/ser' }]" />
		<Button variant="solid" class="ml-auto">New Server</Button>
	</Header>

	<div class="flex gap-3 items-center px-5">
		<TextInput
			placeholder="Search"
			v-model="searchQuery"
			:debounce="500"
			@update:modelValue="v => applyFilters('title', v)"
		>
			<template #prefix>
				<lucide-search class="size-4 text-ink-gray-5" />
			</template></TextInput
		>

		<Select
			placeholder="Region"
			class="!w-fit"
			:options="regions"
			@update:modelValue="v => applyFilters('cluster.title', v)"
		>
			<template #prefix>
				<LucideMapPin class="size-4" />
			</template>
		</Select>

		<Select
			placeholder="Status"
			class="!w-fit"
			:options="['' , 'Active', 'Pending', 'Archived']"
			@update:modelValue="v => applyFilters('status', v)"
		>
			<template #prefix>
				<span class="rounded size-2 bg-gray-500" />
			</template>
		</Select>

		<Button class="ml-auto" @click="toggleSort">
			<template #prefix>
				<LucideArrowUpDown
					v-if='sortBy == "desc"'
					class="size-4 transition-transform"
				/>
				<LucideArrowDownUp v-else class="size-4 transition-transform" />
			</template>
			Sort
		</Button>

		<Button><LucideEllipsis class="size-4" /></Button>
	</div>

	<div class="p-5 text-ink-gray-8 flex flex-col gap-4">
		<section
			v-for="server in servers?.data"
			class="shadow dark:bg-surface-cards rounded"
			:key="server.name"
		>
			<!-- header -->
			<div
				class="border-b dark:border-outline-gray-2  p-4 flex gap-3 items-center"
			>
				<img
					:src="`../../assets/providers/${providerIcons[server?.provider]}.svg`"
					class="size-8"
				/>

				<div class="flex flex-wrap gap-2 items-center text-sm">
					<span>{{ server?.title }}</span>
					<div class="rounded-full size-2 bg-surface-green-3" />
					<span>Active</span>
					<span class="w-full text-ink-gray-6">2 vCPU, 8GB RAM, 160 Disk</span>
				</div>

				<div class="flex items-center gap-1 text-ink-gray-6 ml-auto">
					<LucideMapPin class="size-4" />
					<span>{{ server?.cluster_title }}</span>
					<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
				</div>
			</div>

			<!-- bench column headers -->
			<div
				class="grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] px-4 pt-4 pb-0 items-center text-ink-gray-4 text-sm"
			>
				<span />
				<span>Bench</span>
				<span>Status</span>
				<span>Version</span>
				<span />
			</div>

			<Collapsable
				v-for="(bench, bench_i) in benchesRes[server.name]?.data"
				:key="bench.name"
			>
				<template #header="{ opened, toggle }">
					<div
						class="grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] px-4 py-2 cursor-pointer items-center"
						:class="
							(benchesRes[server.name]?.data.length - 1 == bench_i && opened) ||
							bench_i != benchesRes[server.name]?.data.length - 1
								? 'border-b dark:border-outline-gray-2'
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
						<div class="flex gap-2 items-center">
							<span
								class="size-2 rounded-full"
								:class="bench.active_benches ? 'bg-surface-green-3' : 'bg-surface-gray-4'"
							/>
							{{ bench.active_benches ? 'Active' : 'Awaiting Deploy' }}
						</div>
						<span>{{ bench.version }}</span>
						<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>
					</div>
				</template>

				<!-- site sub-header + rows -->
				<div
					class="grid gap-3 grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] px-4 py-2 items-center border-b dark:border-outline-gray-2 text-sm text-ink-gray-5"
				>
					<span />
					<span class="ml-6">Site</span>
					<span>Status</span>
					<span>Created</span>
					<span />

					<!-- site rows -->
					<template
						v-for="(site, site_i) in sitesRes[bench.name]?.data"
						:key="site.name"
					>
						<span />
						<span class="flex gap-2 items-center text-ink-gray-8 ml-6">
							<LucideAppWindow class="size-4" /> {{ site.name }}
						</span>
						<div class="flex gap-2 items-center text-ink-gray-8">
							<span
								class="size-2 rounded-full"
								:class="site.status === 'Active' ? 'bg-surface-green-3' : site.status === 'Broken' ? 'bg-surface-red-3' : 'bg-surface-orange-3'"
							/>
							{{ site.status }}
						</div>
						<span class="text-ink-gray-8"
							>{{ dayjsLocal(site.creation).fromNow() }}</span
						>
						<Button variant="ghost"><LucideEllipsis class="size-4" /></Button>

						<div
							v-if="site_i != sitesRes[bench.name]?.data.length - 1"
							class="border-b dark:border-outline-gray-2 col-span-full -mx-4"
						/>
					</template>
				</div>
			</Collapsable>
		</section>
	</div>
</template>
