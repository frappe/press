<script setup lang="ts">
import { createListResource, Badge, Select, Button, Tooltip } from 'frappe-ui'
import { date, duration } from '@/utils/format'
import { ref, watch } from 'vue'

interface Props {
	name?: string
}

const props = defineProps<Props>()

const deployBuilds = createListResource({
	doctype: 'Deploy Candidate Build',
	fields: ['name', 'status', 'creation', 'build_duration', 'owner'],
	filters: {
		group: props.name,
	},
	orderBy: 'creation desc',
})

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	fields: ['name', 'status', 'creation', 'team'],
	filters: {
		release_group: props.name,
	},
	orderBy: 'creation desc',
})

const badgeThemes = {
	Running: 'blue',
	Success: 'green',
	Failure: 'red',
	Pending: 'yellow',
	Preparing: 'yellow',
}

const statusOptions = [
	'',
	'Draft',
	'Scheduled',
	'Pending',
	'Preparing',
	'Running',
	'Success',
	'Failure',
]

const mode = ref('newer')

watch(
	mode,
	(x) => {
		if (x === 'newer') {
			pipelines.fetch()
		} else deployBuilds.fetch()
	},
	{ immediate: true },
)

const handleStatusChange = (status: string) => {
	const resObj = mode?.value === 'newer' ? pipelines : deployBuilds
	resObj.filters.status = status
	resObj.reload()
}
</script>

<template>
	<div class="flex items-center gap-2 mb-3">
		<Button @click="mode = 'newer'" v-if="mode == 'older'">
			<template #icon>
				<LucideChevronLeft class="size-4" />
			</template>
		</Button>
		<span class="font-medium" v-if='mode == "older"'> Older Deploys</span>

		<Select
			:options="statusOptions"
			@update:modelValue="handleStatusChange"
			placeholder="Select Status"
			class="max-w-[130px]"
			:class="mode == 'newer'? 'mr-auto' : 'ml-auto'"
		/>

		<Button @click="mode = 'older'" v-if="mode == 'newer'">
			<LucideHistory class="size-4" />
		</Button>

		<Button>
			<lucide-refresh-ccw class="size-4" />
		</Button>

		<Button>
			<template #prefix> <LucideRocket class="size-4" /></template>
			Deploy
		</Button>
	</div>

	<div
		class="bg-surface-gray-2 p-2 rounded  text-ink-gray-4 grid grid-cols-[1fr_0.5fr_0.5fr_1fr]"
	>
		<span class="rounded-l">Deploy</span>
		<span>Status</span>
		<span v-if='mode=="older"'>Duration</span>
		<span v-else />
		<span v-if='mode=="older"' class="rounded-r">Deployed By</span>
		<span v-else />
	</div>

	<br />

	<template
		v-for="item in mode == 'older' ? deployBuilds.data : pipelines.data"
		:key="item.name"
	>
		<router-link
			class="hover:bg-surface-gray-1 p-2 border-b grid grid-cols-[1fr_0.5fr_0.5fr_1fr] gap-2"
			:to="{name: mode=='older' ?'Deploy Candidate':'Release Pipeline', params: {id: item.name,name }}"
		>
			<span>Deploy on {{ date(item.creation) }}</span>

			<Badge
				:label="item.status"
				:theme="badgeThemes[item.status]"
				class="mr-auto"
			>
				<template #suffix v-if="item.addressable_notification">
					<Tooltip text="Attention required!">
						<LucideAlertCircle class="size-3" />
					</Tooltip>
				</template>
			</Badge>

			<span>{{ duration(item.build_duration) }}</span>
			<span>{{ item.owner || item.team }}</span>
		</router-link>
	</template>

	<div class="w-full flex">
		<Button
			v-if="mode == 'older'? deployBuilds.hasNextPage : pipelines.hasNextPage "
			class="ml-auto mt-3"
			@click="mode == 'older'? deployBuilds.next() : pipelines.next()"
		>
			Load more
		</Button>
	</div>
</template>
