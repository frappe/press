<script setup lang="ts">
import {
	Badge,
	Button,
	Combobox,
	Dropdown,
	MultiSelect,
	TextInput,
	Tooltip,
	createDocumentResource,
	createListResource,
} from 'frappe-ui'
import { unparse } from 'papaparse'
import { defineAsyncComponent, h, ref } from 'vue'
import BillingAlerts from '@/components/BillingAlerts.vue'
import LinkControl from '@/components/LinkControl.vue'
import Scrollbar from '@/components/common/Scrollbar.vue'
import Header from '@/components/Header.vue'
import { getTeam } from '@/data/team'
import { clusterOptions } from '@/objects/common'
import { renderDialog } from '@/utils/components'
import { userCurrency } from '@/utils/format'
import { getSiteStatusBadge, trialDays } from '@/utils/site'

const statusOptions = [
	'Active',
	'Inactive',
	'Suspended',
	'Broken',
	'Archived',
].map((label) => ({
	label,
	value: label,
}))
const regionOptions = clusterOptions.filter(Boolean)

const selectedStatuses = ref<string[]>(
	statusOptions.filter((o) => o.value !== 'Archived').map((o) => o.value),
)

const initialFilters = { status: ['in', selectedStatuses.value] }

const sites = createListResource({
	doctype: 'Site',
	fields: [
		'name',
		'host_name',
		'status',
		'creation',
		'trial_end_date',
		'plan.plan_title as plan_title',
		'plan.price_usd as price_usd',
		'plan.price_inr as price_inr',
		'group.title as group_title',
		'group.public as group_public',
		'group.version as version',
		'cluster.image as cluster_image',
		'cluster.title as cluster_title',
	],
	filters: initialFilters,
	orderBy: 'creation desc',
	pageLength: 20,
	auto: true,
	cache: ['Site', 'list'],
})

const sitesCount = createListResource({
	doctype: 'Site',
	fields: ['name'],
	filters: initialFilters,
	orderBy: 'creation desc',
	pageLength: 100000,
	auto: true,
})

const applyStatusFilter = (value: string[]) => {
	selectedStatuses.value = value
	applyFilter('status', value.length ? ['in', value] : undefined)
}

const moreActions = [
	{ label: 'Export as CSV', icon: 'download', onClick: () => exportCSV() },
]

const applyFilter = (key: string, value: any) => {
	const filters = { ...sites.filters, [key]: value || undefined }
	sites.update({ filters, start: 0 })
	sites.reload()
	sitesCount.update({ filters })
	sitesCount.reload()
}

const sitePlan = (row: any) => {
	if (row.trial_end_date) return trialDays(row.trial_end_date)
	const $team = getTeam()
	if (row.price_usd > 0) {
		const india = $team.doc?.currency === 'INR'
		const formattedValue = userCurrency(
			india ? row.price_inr : row.price_usd,
			0,
		)
		return `${formattedValue}/mo`
	}
	return row.plan_title
}

const dropSite = (site: any) => {
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

const siteOptions = (site: any) => {
	return [
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
}

const exportCSV = () => {
	const fields = [
		'host_name',
		'plan_title',
		'cluster_title',
		'group_title',
		'tags',
		'version',
		'creation',
	]
	createListResource({
		doctype: 'Site',
		url: 'press.api.site.fetch_sites_data_for_export',
		auto: true,
		onSuccess(data: any) {
			let csv = unparse({ fields, data })
			csv = '﻿' + csv // for utf-8

			const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
			const today = new Date().toISOString().split('T')[0]
			const filename = `sites-${today}.csv`
			const link = document.createElement('a')
			link.href = URL.createObjectURL(blob)
			link.download = filename
			link.click()
			URL.revokeObjectURL(link.href)
		},
	})
}
</script>

<template>
	<div class="flex flex-col h-dvh">
		<Header class="bg-surface-white shrink-0">
			<Breadcrumbs :items="[{ label: 'Sites', route: '/sites' }]" />
			<Button
				class="ml-auto mr-2"
				:loading="sites.list?.loading"
				@click="sites.reload()"
			>
				<template #icon><lucide-refresh-ccw class="size-4" /></template>
			</Button>
			<Button class="mr-2" :route="{ name: 'New Site' }" variant="solid">
				<template #prefix><lucide-plus class="size-4" /></template>
				New Site
			</Button>
			<Dropdown :options="moreActions">
				<Button>
					Actions
					<template #suffix><LucideChevronsUpDown class="size-4" /></template>
				</Button>
			</Dropdown>
		</Header>

		<div class="px-5 pt-4">
			<BillingAlerts ctx-type="List Page" />
		</div>

		<div class="flex items-center gap-2 px-5 pb-3 overflow-auto">
			<TextInput
				placeholder="Search sites"
				class="w-56 shrink-0"
				:debounce="500"
				@update:modelValue="v => applyFilter('_search', v || undefined)"
			>
				<template #prefix>
					<lucide-search class="size-4 text-ink-gray-5" />
				</template>
			</TextInput>

			<MultiSelect
				placeholder="Status"
				class="!w-36 shrink-0 status-multiselect *:text-ink-gray-5"
				:options="statusOptions"
				:modelValue="selectedStatuses"
				@update:modelValue="applyStatusFilter"
			>
				<template #option="{ item }">
					<span class="site-status-option flex items-center gap-1.5 flex-1">
						<span
							class="size-3.5 rounded-sm border shrink-0 flex items-center justify-center"
							:class="selectedStatuses.includes(item.value)
									? 'bg-surface-gray-7 border-outline-gray-5'
									: 'border-outline-gray-3'"
						>
							<lucide-check
								v-if="selectedStatuses.includes(item.value)"
								class="size-2 text-ink-white"
								stroke-width="3"
							/>
						</span>
						<span
							class="size-2 rounded-full shrink-0 ml-1"
							:class="getSiteStatusBadge(item.value).dot"
						/>
						{{ item.label }}
					</span>
				</template>
			</MultiSelect>

			<LinkControl
				placeholder="Version"
				class="!w-36 shrink-0"
				:options="{ doctype: 'Frappe Version' }"
				:modelValue="sites.filters?.['group.version']"
				@update:modelValue="v => applyFilter('group.version', v)"
			/>

			<LinkControl
				placeholder="Benches"
				class="!w-36 shrink-0"
				:options="{ doctype: 'Release Group' }"
				:modelValue="sites.filters?.group"
				@update:modelValue="v => applyFilter('group', v)"
			/>

			<Combobox
				placeholder="Region"
				class="!w-36 shrink-0"
				:openOnFocus="true"
				:options="regionOptions"
				@update:modelValue="v => applyFilter('cluster', v)"
			>
				<template #prefix>
					<LucideGlobe class="size-4 text-ink-gray-5" />
				</template>
			</Combobox>

			<LinkControl
				placeholder="Tag"
				class="!w-32 shrink-0"
				:options="{ doctype: 'Press Tag', filters: { doctype_name: 'Site' } }"
				:modelValue="sites.filters?.['tags.tag']"
				@update:modelValue="v => applyFilter('tags.tag', v)"
			/>
		</div>

		<Scrollbar class="flex-1 min-h-0 px-5">
			<table class="sites-table w-full">
				<thead class="text-ink-gray-5 text-sm">
					<tr>
						<th class="rounded-l">Site</th>
						<th>Status</th>
						<th>Plan</th>
						<th>Region</th>
						<th>Benches</th>
						<th>Version</th>
						<th class="rounded-r"></th>
					</tr>
				</thead>

				<tbody class="text-ink-gray-8">
					<tr v-if="sites.list?.loading && !sites.data?.length">
						<td colspan="7">
							<div class="flex items-center justify-center py-20">
								<Spinner class="size-5" />
							</div>
						</td>
					</tr>

					<tr v-for="site in sites.data" :key="site.name" class="*:border-b">
						<td class="font-medium">
							<Tooltip text="Go to site dashboard">
								<router-link
									class="flex gap-2 w-fit items-center hover:underline"
									:to="{ name: 'Site Detail', params: { name: site.name } }"
								>
									{{ site.host_name || site.name }}
								</router-link>
							</Tooltip>
						</td>

						<td>
							<Badge
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
						</td>

						<td> {{ sitePlan(site) }} </td>

						<td>
							<span class="flex gap-1.5 items-center">
								<img
									v-if="site.cluster_image"
									:src="site.cluster_image"
									class="size-3.5"
								/>
								{{ site.cluster_title }}
							</span>
						</td>

						<td>
							{{ site.group_public ? 'Shared' : site.group_title }}
						</td>
						<td> {{ site.version }}</td>

						<td class="w-px">
							<div class="flex justify-end">
								<Dropdown :options="siteOptions(site)">
									<Button variant="ghost"
										><LucideEllipsis class="size-4" /></Button
									>
								</Dropdown>
							</div>
						</td>
					</tr>
				</tbody>
			</table>

			<div
				v-if="!sites.list?.loading && !sites.data?.length"
				class="py-10 text-center text-sm text-ink-gray-5"
			>
				No sites
			</div>
		</Scrollbar>

		<div class="shrink-0 px-5 py-2 flex justify-end items-center gap-3">
			<span class="text-sm text-ink-gray-5">
				Total {{ sitesCount.data?.length ?? 0 }}
				{{ sitesCount.data?.length === 1 ? 'site' : 'sites' }}
			</span>
			<Button
				v-if="sites.hasNextPage"
				:loading="sites.list?.loading"
				@click="sites.next()"
			>
				Load more
			</Button>
		</div>
	</div>
</template>

<style scoped>
.sites-table th {
	@apply p-2 sticky top-0 z-10 bg-surface-gray-1 text-left font-normal;
}

.sites-table td {
	@apply p-2 whitespace-nowrap;
}
</style>

<style>
/* add shrink-0 to multiselect chevron */
.status-multiselect svg {
	flex-shrink: 0;
}

/* Hide MultiSelect's built-in checkmark*/
.site-status-option ~ .absolute.right-2 {
	display: none;
}
</style>
