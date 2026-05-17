<script setup lang="ts">
import {
	createResource,
	createDocumentResource,
	getCachedDocumentResource,
	Button,
	Dropdown,
	Badge,
	Tabs,
} from 'frappe-ui'



import Stages from './Stages.vue'
import CopyBtn from '@/components/utils/CopyBtn.vue'

import { h, ref, computed, provide } from 'vue'
import { useRoute } from 'vue-router'
import { getTeam } from '@/data/team'

import { duration, date } from '@/utils/format'

const route = useRoute()
const team = getTeam()
const output = ref<String | null>(null)

const setOutput = (str: String | null) => {
	output.value = str
}

provide('setOutput', setOutput)
provide('output', output)

const dropdownOptions = computed(() => {
	const list = [
		{
			label: 'View in Desk',
			icon: 'external-link',
			condition: () => team?.doc?.is_desk_user,
			onClick: () => {
				window.open(
					`${window.location.protocol}//${window.location.host}/app/deploy-candidate-build/${this.id}`,
					'_blank',
				)
			},
		},
		{
			label: 'View App Versions',
			icon: 'package',
			onClick: () => {
				// this.appVersions();
			},
		},
	]

	return list.filter((option) => option.condition?.() ?? true)
})

const buildIds = computed(() => {
	const ids = pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => x.name)
	return ids || []
})

const pipeline = createDocumentResource({
	doctype: 'Release Pipeline',
	name: route.params.id,
	auto: true,
})

const cardLabels = computed(() => {
	return {
		'Created by': 'sidhanth@frappe.io',
		Start: date(pipeline?.doc?.steps?.start, 'lll'),
		End: date(pipeline?.doc?.steps?.end, 'lll'),
		Duration: 10,
		// Duration: duration(data?.doc?.steps?.duration),
	}
})

const tabState = ref(0)
const sidebarTabs = ref([
	{
		label: 'Tasks',
		icon: LucideWorkflow,
	},
	{
		label: 'Issues',
		icon: LucideAlertCircle,
	},
])
</script>

<template>
	<main
		class="pipeline-page flex flex-col gap-5 py-3 px-5 w-full h-[calc(100dvh-6rem)]"
	>
		<!-- header -->
		<div class="flex gap-2 items-center">
			<button>
				<lucide-chevron-left class="size-4" />
			</button>

			<h2 class="text-ink-gray-9">deploy blablablab</h2>
			<Badge :label="'Running'" />

			<Button theme="red" class="ml-auto"> Stop Deploy </Button>

			<Button>
				<lucide-refresh-ccw class="h-4 w-4" />
			</Button>

			<Dropdown v-if="dropdownOptions?.length" :options="dropdownOptions">
				<template v-slot="{ open }">
					<Button>
						<template #icon>
							<lucide-more-horizontal class="h-4 w-4" />
						</template>
					</Button>
				</template>
			</Dropdown>
		</div>

		<!-- status cards -->
		<section class="grid grid-cols-4 gap-5">
			<div
				v-for="(label, key) in cardLabels"
				:key="key"
				class="flex flex-col gap-2 border p-4 rounded"
			>
				<span class="text-sm font-medium text-ink-gray-4"> {{ key }} </span>
				<span class="text-sm text-ink-gray-9"> {{ label || '-' }} </span>
			</div>
		</section>

		<!-- deploy steps + output -->
		<div
			class="grid rounded border p-3 flex-1 transition-all duration-500 min-h-0"
			:class="[output ? 'grid-cols-[auto_1fr]' : 'grid-cols-[1fr_0fr] pr-0']"
		>
			<aside
				class="w-full !min-w-[10rem] pr-3 overflow-y-auto overflow-x-hidden px-2"
			>
				<Tabs
					:tabs="sidebarTabs"
					v-model="tabState"
					class="[&_[role=tablist]]:mb-2 [&_[role=tablist]]:px-0"
				>
					<template #tab-item="{ tab }">
						<button class="flex items-center gap-2 pb-3">
							<component :is="tab.icon" class="size-4 text-ink-gray-6" />
							{{ tab.label }}

							<Badge v-if='tab.label == "Issues"' :label="0" />
						</button>
					</template>
				</Tabs>

				<Stages
					v-if="tabState == 0 "
					:stages="pipeline?.doc?.steps?.stages"
					:buildIds
				/>
			</aside>

			<div
				v-show="output"
				class="overflow-hidden bg-surface-gray-1 dark:bg-surface-cards p-3 rounded flex-1"
			>
				<div
					class="flex items-center gap-2 border-b pb-2 border-outline-gray-2 mb-3 text-ink-gray-6"
				>
					<span>Output</span>
					<CopyBtn :text="output" class="ml-auto" />
					<button @click="setOutput(null)">
						<lucide-x class="size-4" />
					</button>
				</div>

				<pre class="font-mono text-xs overflow-auto">{{output}}</pre>
			</div>
		</div>
	</main>
</template>

<style>
body:has(.pipeline-page) #scrollContainer {
	overflow: hidden;
	height: 100%;
}
</style>
