<script setup lang="ts">
import { Button, createListResource, TextInput, Combobox } from 'frappe-ui'
import Header from '@/components/Header.vue'
import { ref } from 'vue'

import ServerCard from './ServerCard.vue'
import Loader from './Loader.vue'

const sortBy = ref('desc')

const servers = createListResource({
	doctype: 'Server',
	auto: true,
	pageLength: 10,
	cache: 'servers list',
	fields: [
		'name',
		'title',
		'status',
		'provider',
		'database_server',
		'plan.title as plan_title',
		'plan.price_usd as price_usd',
		'plan.price_inr as price_inr',
		'cluster.name as cluster',
		'cluster.image as cluster_image',
		'cluster.title as cluster_title',
		'cluster.country as cluster_country',
		'is_unified_server',
		'plan.vcpu as vcpu',
		'plan.memory as memory',
		'plan.disk as disk',
	],
	orderBy: `creation ${sortBy.value}`,
})

const regionOptions = [
	{ label: 'Bahrain', value: 'Bahrain' },
	{ label: 'Cape Town', value: 'Cape Town' },
	{ label: 'Frankfurt', value: 'Frankfurt' },
	{ label: 'KSA', value: 'KSA' },
	{ label: 'London', value: 'London' },
	{ label: 'Mumbai', value: 'Mumbai' },
	{ label: 'Singapore', value: 'Singapore' },
	{ label: 'UAE', value: 'UAE' },
	{ label: 'Virginia', value: 'Virginia' },
	{ label: 'Zurich', value: 'Zurich' },
]

const statusOptions = [
	{ label: 'Active', value: 'Active' },
	{ label: 'Pending', value: 'pending' },
	{
		label: 'Archived',
		value: 'archived',
	},
]

const applyFilters = (key: string, value: any) => {
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
		<Button class="ml-auto mr-2" @click="servers.reload()">
			<template #icon>
				<lucide-refresh-ccw class="size-4" />
			</template>
		</Button>

		<Button :route="{ name: 'New Server' }" variant="solid">
			New Server
		</Button>
	</Header>

	<!-- filters -->
	<div class="flex gap-3 items-center px-5">
		<TextInput
			placeholder="Search server"
			:debounce="500"
			@update:modelValue="v => applyFilters('title', ['like', `%${v.toLowerCase()}%`])"
		>
			<template #prefix>
				<lucide-search class="size-4 text-ink-gray-5" />
			</template></TextInput
		>

		<Combobox
			placeholder="Region"
			:openOnFocus="true"
			class="!w-36"
			:options="regionOptions"
			@update:modelValue="v => applyFilters('cluster.title', v)"
		>
			<template #prefix>
				<LucideMapPin class="size-4" />
			</template>
		</Combobox>

		<Combobox
			placeholder="Status"
			class="!w-32"
			:openOnFocus="true"
			:options="regionOptions"
			@update:modelValue="v => applyFilters('status', v)"
		>
			<template #prefix>
				<span class="rounded size-2 bg-gray-500 shrink-0" />
			</template>
		</Combobox>

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
