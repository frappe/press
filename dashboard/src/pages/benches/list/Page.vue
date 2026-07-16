<script setup lang="ts">
import { Button, createListResource, Spinner, TextInput } from 'frappe-ui'
import Header from '@/components/Header.vue'
import LinkControl from '@/components/LinkControl.vue'
import BenchRow from './BenchRow.vue'

const groups = createListResource({
	doctype: 'Release Group',
	auto: true,
	pageLength: 20,
	cache: 'bench-list-groups',
	fields: [
		'name',
		'title',
		'version',
		'active_benches',
		'site_count',
		'server',
		'server_title',
		'server.provider as server_provider',
		{ apps: ['app'] },
	],
	orderBy: 'creation desc',
})

const applyFilter = (key: string, val: any) => {
	groups.update({
		filters: { ...groups.filters, [key]: val || undefined },
		start: 0,
	})
	groups.reload()
}
</script>

<template>
	<div class="flex flex-col h-full">
		<Header class="bg-surface-white shrink-0">
			<Breadcrumbs :items="[{ label: 'Benches', route: '/groups' }]" />
			<Button class="ml-auto mr-2" @click="groups.reload()">
				<template #icon><lucide-refresh-ccw class="size-4" /></template>
			</Button>
			<Button :route="{ name: 'New Release Group' }" variant="solid"
				>New Bench</Button
			>
		</Header>

		<div class="flex gap-3 items-center px-5 py-3 shrink-0">
			<TextInput
				placeholder="Search bench"
				:debounce="500"
				@update:modelValue="v => applyFilter('title', v ? ['like', `%${v}%`] : undefined)"
			>
				<template #prefix>
					<lucide-search class="size-4 text-ink-gray-5" />
				</template>
			</TextInput>

			<LinkControl
				placeholder="Version"
				class="!w-36"
				:options="{ doctype: 'Frappe Version' }"
				@update:modelValue="v => applyFilter('version', v)"
			/>

			<LinkControl
				placeholder="Tag"
				class="!w-32"
				:options="{ doctype: 'Press Tag', filters: { doctype_name: 'Release Group' } }"
				@update:modelValue="v => applyFilter('tags.tag', v)"
			/>
		</div>

		<div class="flex-1 min-h-0 overflow-y-auto px-5">
			<div
				v-if="groups.list?.loading && !groups.data?.length"
				class="flex justify-center py-10"
			>
				<Spinner class="size-5" />
			</div>

			<div v-else class="overflow-x-auto pb-5">
				<div class="min-w-[44rem]">
					<div
						class="bench-grid px-2 py-2 text-xs text-ink-gray-5 bg-surface-gray-1 rounded"
					>
						<span />
						<span>Title</span>
						<span>Status</span>
						<span>Version</span>
						<span>Apps</span>
						<span />
					</div>

					<BenchRow
						v-for="(group, i) in groups.data"
						:key="group.name"
						:data="group"
						:isLast="i === (groups.data?.length ?? 0) - 1"
					/>

					<div
						v-if="!groups.data?.length"
						class="py-10 text-center text-sm text-ink-gray-5"
					>
						No benches
					</div>
				</div>
			</div>
		</div>

		<div v-if="groups.hasNextPage" class="shrink-0 px-5 py-2 flex justify-end">
			<Button :loading="groups.list?.loading" @click="groups.next()"
				>Load more</Button
			>
		</div>
	</div>
</template>

<style scoped>
.bench-grid {
	@apply grid gap-3 grid-cols-[1.5rem_2fr_1fr_0.6fr_1fr_2rem];
}
</style>
