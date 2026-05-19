<script setup lang="ts">
import {
	createListResource,
	createDocumentResource,
	Button,
	Dropdown,
	Badge,
} from 'frappe-ui'

import Tabs from '@/components/common/Tabs.vue'

import Stages from './Stages.vue'
import CopyBtn from '@/components/utils/CopyBtn.vue'
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'

import { ref, computed, provide, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { getTeam } from '@/data/team'

import { secsToDuration, date } from '@/utils/format'

const team = getTeam()
const route = useRoute()
const socket = window.$socket
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
					`${window.location.protocol}//${window.location.host}/app/release-pipeline/${route.params.id}`,
					'_blank',
				)
			},
		},
	]

	return list.filter((option) => option.condition?.() ?? true)
})

const activeBuildId = ref()
const buildIds = computed(() => {
	const ids = pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => x.name)
	if (!activeBuildId.value && ids) activeBuildId.value = ids[0]
	return ids || []
})

const pipeline = createDocumentResource({
	doctype: 'Release Pipeline',
	name: route.params.id,
	auto: true,
})

const notifApiFields = {
	doctype: 'Press Notification',
	fields: [
		'name',
		'title',
		'message',
		'document_name',
		'class',
		'assistance_url',
	],
	filters: { document_type: 'Deploy Candidate Build', is_actionable: true },
}

const errors = createListResource(notifApiFields)
const warnings = createListResource(notifApiFields)

watch(
	() => buildIds.value,
	(x) => {
		if (!x) return

		errors.update({
			cache: [
				'Press Notification Error',
				'Deploy Candidate Build',
				buildIds.value,
			],
			filters: { document_name: ['in', buildIds.value], class: 'Error' },
		})
		errors.fetch()

		warnings.update({
			cache: [
				'Press Notification Warning',
				'Deploy Candidate Build',
				buildIds.value,
			],
			filters: { document_name: ['in', buildIds.value], class: 'Warning' },
		})
		warnings.fetch()
	},
)

const tabState = ref('Tasks')

const sidebarTabs = ref([
	{ label: 'Tasks', icon: LucideWorkflow },
	{ label: 'Issues', icon: LucideAlertCircle },
])

const badgeThemes = {
	Pending: 'gray',
	Running: 'blue',
	'Partial Success': 'yellow',
	Success: 'green',
	Failure: 'red',
	Retrying: 'yellow',
}

// ---------------------  Realtime stuff ----------------------
const handleDocUpdate = (x) => {
	if (x.doctype === 'Release Pipeline' && x.name === route.params.id)
		pipeline.reload()
}

onMounted(() => {
	socket.emit('doc_subscribe', 'Release Pipeline', route.params.id)
	socket.on('doc_update', handleDocUpdate)
})

onBeforeUnmount(() => {
	socket.emit('doc_unsubscribe', 'Release Pipeline', route.params.id)
	socket.off('doc_update', handleDocUpdate)
})
</script>

<template>
	<main
		class="pipeline-page flex flex-col gap-5 py-3 px-5 w-full h-[calc(100dvh-6rem)]"
	>
		<!-- header -->
		<div class="flex gap-2 items-center">
			<router-link :to="`/groups/${route.params.name}/pipelines`">
				<lucide-chevron-left class="size-4" />
			</router-link>

			<h2 class="text-ink-gray-9">Pipeline {{ pipeline?.doc?.name }}</h2>

			<Badge
				:label="pipeline?.doc?.status"
				:theme="badgeThemes[pipeline?.doc?.status] || 'gray'"
				class="mr-auto"
			/>

			<Tabs
				variant="solid"
				v-if="buildIds.length > 1"
				:tabs="pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => ({ label: x.architecture,  value: x.name }))"
				v-model="activeBuildId"
				class=" [&_[role=tablist]]:w-fit"
			/>

			<Dropdown v-if="dropdownOptions?.length" :options="dropdownOptions">
				<Button>
					<lucide-more-horizontal class="size-4" />
				</Button>
			</Dropdown>
		</div>

		<!-- status cards -->
		<section
			class="grid grid-cols-4 gap-5 [&_b]:text-ink-gray-4 [&_b]:font-normal text-sm"
		>
			<div class="flex flex-col gap-2 border p-4 rounded ">
				<b> Created by </b>
				<span class="text-ink-gray-9">{{ pipeline?.doc?.owner }} </span>
			</div>

			<div class="flex flex-col gap-2 border p-4 rounded">
				<b> Start </b>
				<span> {{ date(pipeline?.doc?.steps?.start) || '-' }} </span>
			</div>

			<div class="flex flex-col gap-2 border p-4 rounded">
				<b> End </b>
				<span> {{ date(pipeline?.doc?.steps?.end)  || '-' }} </span>
			</div>

			<div class="flex flex-col gap-2 border p-4 rounded">
				<b> Duration </b>
				<span> {{ secsToDuration(pipeline?.doc?.steps?.duration)  || '-' }} </span>
			</div>
		</section>

		<!-- deploy steps + output -->
		<div
			class="grid rounded border p-3 flex-1 transition-all duration-500 min-h-0"
			:class="[output ? 'grid-cols-[auto_1fr]' : 'grid-cols-[1fr_0fr] pr-0']"
		>
			<aside
				class="w-full !min-w-[30rem] pr-3 overflow-y-auto overflow-x-hidden px-0.5"
			>
				<div class="flex items-center gap-3  [&_[rol=tablist]]:px-0 mb-2 t-2">
					<Tabs
						class="w-full"
						tablistClass="!px-0"
						:tabs="sidebarTabs"
						v-model="tabState"
					>
						<template #suffix="{ tab }">
							<span
								v-if='tab.label == "Issues"'
								class="bg-surface-gray-2 py-0.5 px-1 rounded text-xs leading-none"
							>
								{{ (errors?.data?.length || 0 ) + (warnings?.data?.length || 0) }}</span
							>
						</template>
					</Tabs>
				</div>

				<Stages
					v-if="tabState == 'Tasks'"
					:stages="pipeline?.doc?.steps?.stages"
					:buildIds
					:activeBuildId
				/>

				<!-- list of errors -->
				<section v-else>
					<div
						v-for='x in [...errors?.data || [], ...warnings?.data || [] ]?.filter(x => x.document_name == activeBuildId)'
						class="flex flex-col gap-1"
					>
						<Collapsable headerCss="py-2" class="mb-3">
							<template #header>
								<StatusIcon :status=" x.class=='Error'? 'Failed': 'Warning'" />

								{{ x.title }}
								{{ x.class }}
								{{ x.document_name }}
							</template>

							<div
								v-html="x.message"
								class="leading-relaxed rounded p-3 ml-3 mb-3 text-sm"
								:class='x.class=="Error"? " bg-surface-red-1 text-ink-red-4" :  "bg-surface-amber-1 text-ink-amber-3"'
							/>

							<div class="w-full flex justify-end">
								<a
									:href="x.assistance_url"
									target="_blank"
									class="bg-surface-gray-1 p-1.5 px-2.5 rounded hover:opacity-70"
								>
									Fix
								</a>
							</div>
						</Collapsable>
					</div>
				</section>
			</aside>

			<!-- output -->
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
