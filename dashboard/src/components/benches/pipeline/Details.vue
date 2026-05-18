<script setup lang="ts">
import {
<<<<<<< HEAD
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
=======
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

import { ref, computed, provide, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { getTeam } from '@/data/team'

import { secsToDuration, date } from '@/utils/format'

const socket = window.$socket
const route = useRoute()
const team = getTeam()
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
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
<<<<<<< HEAD
					`${window.location.protocol}//${window.location.host}/app/release-pipeline/${route.params.id}`,
=======
					`${window.location.protocol}//${window.location.host}/app/deploy-candidate-build/${this.id}`,
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
					'_blank',
				)
			},
		},
<<<<<<< HEAD
=======
		{
			label: 'View App Versions',
			icon: 'package',
			onClick: () => {
				// this.appVersions();
			},
		},
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
	]

	return list.filter((option) => option.condition?.() ?? true)
})

<<<<<<< HEAD
const activeBuildId = ref()
const buildIds = computed(() => {
	const ids = pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => x.name)
	if (!activeBuildId.value && ids) activeBuildId.value = ids[0]
=======
const buildIds = computed(() => {
	const ids = pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => x.name)
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
	return ids || []
})

const pipeline = createDocumentResource({
	doctype: 'Release Pipeline',
	name: route.params.id,
	auto: true,
})

<<<<<<< HEAD
<<<<<<< HEAD
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
=======
=======
watch(
	() => pipeline.doc,
	(newVal, oldVal) => {
		console.log('pipeline updated', newVal)
	},
)

>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
const cardLabels = computed(() => {
	return {
		'Created by': 'sidhanth@frappe.io',
		Start: date(pipeline?.doc?.steps?.start, 'lll'),
		End: date(pipeline?.doc?.steps?.end, 'lll'),
		Duration: secsToDuration(pipeline?.doc?.steps?.duration),
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
<<<<<<< HEAD
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======

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
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
</script>

<template>
	<main
		class="pipeline-page flex flex-col gap-5 py-3 px-5 w-full h-[calc(100dvh-6rem)]"
	>
		<!-- header -->
		<div class="flex gap-2 items-center">
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
			<button>
=======
			<router-link :to="`/groups/${route.params.name}/pipelines`">
>>>>>>> 7f92d4e83 (fix(deploy-ui): add badge status colors)
				<lucide-chevron-left class="size-4" />
			</router-link>

			<h2 class="text-ink-gray-9">pipeline {{ pipeline?.doc?.name }}</h2>
			<Badge
				:label="pipeline?.doc?.status"
				:theme="badgeThemes[pipeline?.doc?.status] || 'gray'"
			/>

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
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
			</Dropdown>
		</div>

		<!-- status cards -->
<<<<<<< HEAD
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
				<span>
					{{ secsToDuration(pipeline?.doc?.steps?.duration)  || '-' }}
				</span>
=======
		<section class="grid grid-cols-4 gap-5">
			<div
				v-for="(label, key) in cardLabels"
				:key="key"
				class="flex flex-col gap-2 border p-4 rounded"
			>
				<span class="text-sm font-medium text-ink-gray-4"> {{ key }} </span>
				<span class="text-sm text-ink-gray-9"> {{ label || '-' }} </span>
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
			</div>
		</section>

		<!-- deploy steps + output -->
<<<<<<< HEAD
		<div class="flex rounded border p-3 flex-1 min-h-0">
			<aside
				class="overflow-y-auto overflow-x-hidden pr-3 px-0.5 flex-shrink-0 transition-all duration-500"
				:class="output ? 'w-[30rem]' : 'w-full'"
			>
				<div class="flex items-center gap-3 mb-3">
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
						<Collapsable headerCss="py-3" class="mb-3">
							<template #header>
								<StatusIcon :status=" x.class=='Error'? 'Failed': 'Warning'" />
								{{ x.title }}
								{{ x.class }}
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
				class="overflow-hidden bg-surface-gray-1 dark:bg-surface-cards p-3 rounded transition-all duration-500 flex-1"
=======
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

			<!-- output -->
			<div
				v-show="output"
				class="overflow-hidden bg-surface-gray-1 dark:bg-surface-cards p-3 rounded flex-1"
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
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
