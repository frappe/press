<script setup lang="ts">
import { Button, createListResource, TextInput, Select } from 'frappe-ui'
import Header from '@/components/Header.vue'
import { ref, watch } from 'vue'

import ServerCard from './ServerCard.vue'
import Loader from './Loader.vue'

const searchQuery = ref('')
const sortBy = ref('desc')

const servers = createListResource({
	doctype: 'Server',
	auto: true,
	pageLength: 10,
	cache: 'servers list',
	fields: [
		'name',
		'title',
		'provider',
		'database_server',
		'plan.title as plan_title',
		'plan.price_usd as price_usd',
		'plan.price_inr as price_inr',
		'cluster.name as cluster',
		'cluster.image as cluster_image',
		'cluster.title as cluster_title',
		'is_unified_server',
	],
	orderBy: `creation ${sortBy.value}`,
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
</script>

<template>
	<Header class="sticky top-0 z-10 bg-surface-white mb-5">
		<Breadcrumbs :items="[{ label: 'Servers', route: '/ser' }]" />
		<Button variant="solid" class="ml-auto">New Server</Button>
	</Header>

	<!-- filters -->
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
			w
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
		<Loader v-if="servers?.list?.loading" />

		<template v-else>
			<ServerCard
				v-for="server in servers.data"
				:key="server.name"
				:data="server"
			/>
		</template>

		<Button
			class="ml-auto"
			v-if="servers?.hasNextPage"
			@click="servers?.next()"
		>
			Load more
		</Button>
	</div>
</template>
