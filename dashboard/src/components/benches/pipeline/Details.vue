<script setup lang="ts">
import {
	createResource,
	createListResource,
	createDocumentResource,
	getCachedDocumentResource,
	Button,
	Dropdown,
	Badge,
} from 'frappe-ui'

import { toast } from 'vue-sonner'
import Tabs from '@/components/common/Tabs.vue'

import CopyBtn from '@/components/utils/CopyBtn.vue'
import Scrollbar from '@/components/common/Scrollbar.vue'
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'
import AppVersionsDialog from '@/dialogs/AppVersionsDialog.vue'

import {
	h,
	ref,
	reactive,
	computed,
	watch,
	onMounted,
	onBeforeUnmount,
} from 'vue'
import { confirmDialog, renderDialog } from '@/utils/components'
import { getTeam } from '@/data/team'

import { secsToDuration, date, duration } from '@/utils/format'

const team = getTeam()
const socket = window.$socket

interface Props {
	deployview: boolean
	id?: string
	// bench  name
	name?: string
}

const props = withDefaults(defineProps<Props>(), {
	deployview: false,
})

const output = reactive({
	val: 'No Output',
	status: null,
	selectedIndex: null,
})

// single line commands with && are very long
// so make them long
const formatCmd = (cmd: string) => {
	return cmd
		.split('&&')
		.map((part) => part.trim())
		.join(' &&\n')
}

const setOutput = (opts) => {
	output.val = opts.val
	output.status = opts.status
	output.selectedIndex = opts.selectedIndex
}

const activeBuildId = ref(props.deployview ? props.id : null)

const buildIds = props.deployview
	? ref([props.id])
	: computed(() => {
			const ids = pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => x.name)
			if (!activeBuildId.value && ids) activeBuildId.value = ids[0]
			return ids || []
		})

const pipeline = props.deployview
	? null
	: createDocumentResource({
			doctype: 'Release Pipeline',
			name: props.id,
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

// used to unsubscribe from socket events
const wired = new Set<string>()
const builds = ref<Record<string, any>>({})

const dummyStages = ref([
	{ label: 'Pre-release checks', status: 'Success' },
	{ label: 'Preparing for deployment', status: 'Success' },
	{ label: 'Building', status: 'Pending' },
	{ label: 'Deploying', status: 'Pending' },
])

const handleDummyStage = (x) => {
	if (!props.deployview) return

	// updateDeployViewBuild(x)
	dummyStages.value[2].status = x.status

	const pendingState = ['Success', 'Failure'].includes(x.status)
		? x.status
		: 'Pending'
	dummyStages.value[3].status = pendingState
}

watch(
	() => buildIds.value,
	(ids: string[]) => {
		if (!ids) return

		ids.forEach((id: string) => {
			if (!builds.value[id]) {
				builds.value[id] = createDocumentResource({
					doctype: 'Deploy Candidate Build',
					name: id,
					auto: true,
					onSuccess: handleDummyStage,
				})

				if (builds.value[id]?.doc) {
					handleDummyStage(builds.value[id].doc)
				}
			}

			// socket io stuff
			if (socket && !wired.has(id)) {
				socket.emit('doc_subscribe', 'Deploy Candidate Build', id)

				socket.on(`bench_deploy:${id}:steps`, (data) => {
					const buildRes = builds.value[id]
					if (data.name === id && buildRes) {
						buildRes.doc.build_steps = data.steps
					}
				})

				socket.on(`bench_deploy:${id}:finished`, () => {
					builds.value[id]?.reload()

					const rgDoc = getCachedDocumentResource(
						'Release Group',
						builds.value[id]?.doc?.group,
					)
					if (rgDoc) rgDoc.reload()

					errors.reload()
					warnings.reload()
				})
			}

			wired.add(id)
		})

		// ------------------------- errors and warnings
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
	{ immediate: true, deep: true },
)

// ---------------------  Realtime stuff ----------------------
const handleDocUpdate = props.deployview
	? null
	: (x) => {
			console.log(x, 'bro')
			if (x.doctype === 'Release Pipeline' && x.name === props.id)
				pipeline.reload()
		}

onBeforeUnmount(() => {
	if (!props.deployview) {
		socket.emit('doc_unsubscribe', 'Release Pipeline', props.id)
		socket.off('doc_update', handleDocUpdate)
		return
	}

	wired.forEach((id) => {
		socket.emit('doc_unsubscribe', 'Deploy Candidate Build', id)
		socket.off(`bench_deploy:${id}:steps`)
		socket.off(`bench_deploy:${id}:finished`)
	})
})

if (!props.deployview) {
	onMounted(() => {
		socket.emit('doc_subscribe', 'Release Pipeline', props.id)
		socket.on('doc_update', handleDocUpdate)
	})
}

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

const dropdownOptions = computed(() => {
	const list = [
		{
			label: 'View in Desk',
			icon: 'external-link',
			condition: () => team?.doc?.is_desk_user,
			onClick: () => {
				const pathname = props.deployview
					? 'deploy-candidate-build'
					: 'release-pipeline'

				window.open(
					`${window.location.protocol}//${window.location.host}/app/${pathname}/${props.id}`,
					'_blank',
				)
			},
		},
		{
			label: 'View App Versions',
			icon: 'package',
			onClick: appVersions,
			condition: () =>
				props.deployview && builds.value[activeBuildId.value]?.doc?.group,
		},
	]

	return list.filter((option) => option.condition?.() ?? true)
})

const appVersions = () => {
	const deploy = builds.value[activeBuildId.value]?.doc
	renderDialog(
		h(AppVersionsDialog, {
			dc_name: deploy.name,
			group: deploy.group,
			status: deploy.status,
		}),
	)
}

const stopBuild = () => {
	const deploy = builds.value[activeBuildId.value]?.doc

	confirmDialog({
		title: 'Fail Running Build',
		message: `
				Are you sure you want to fail this running build?<br><br>
				<div class="text-bg-base bg-surface-gray-2 p-2 rounded-md">
				This will <strong>stop the current build immediately</strong>.  
				All progress made so far will be <strong>discarded</strong>, and the next triggered build will start from scratch.
				<br><br>
				Use this option if a build is stuck, taking unusually long, or is expected to fail.
				</div>
				`,
		primaryAction: {
			label: 'Stop Build',
			variant: 'solid',
			theme: 'red',
			onClick({ hide }) {
				createResource({
					url: 'press.api.bench.fail_build',
					params: { dn: deploy.name },
				})
					.fetch()
					.then(() => {
						hide()
					})
					.catch(() => {
						hide()
						toast.error(
							'Unable to stop build please wait for the status to be updated',
						)
					})
			},
		},
	})
}
</script>

<template>
	<main
		class="pipeline-page flex flex-col gap-4 py-3 px-5 w-full h-[calc(100dvh-6rem)]"
	>
		<!-- header -->
		<div class="flex gap-2 items-center">
			<router-link :to="`/groups/${name}/${deployview? 'deploys':'pipelines'}`">
				<lucide-chevron-left class="size-4" />
			</router-link>

			<h2 class="text-ink-gray-9">
				{{ deployview ? builds[activeBuildId]?.doc?.deploy_candidate : "Pipeline" }}
				{{ pipeline?.doc?.name }}
			</h2>

			<Badge
				:label="deployview ? builds[activeBuildId]?.doc?.status : pipeline?.doc?.status"
				:theme="badgeThemes[deployview ? builds[activeBuildId]?.doc?.status : pipeline?.doc?.status] || 'gray'"
				class="mr-auto"
			/>

			<Tabs
				variant="solid"
				v-if="!deployview && buildIds.length > 1"
				:tabs="pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => ({ label: x.architecture, value: x.name }))"
				v-model="activeBuildId"
				class=" [&_[role=tablist]]:w-fit"
			/>

			<Button
				@click="stopBuild"
				v-if="deployview && builds[activeBuildId]?.doc?.status === 'Running'"
				theme="red"
			>
				Stop Deploy
			</Button>

			<Dropdown v-if="dropdownOptions?.length" :options="dropdownOptions">
				<Button>
					<lucide-more-horizontal class="size-4" />
				</Button>
			</Dropdown>
		</div>

		<!-- status cards -->
		<section
			class="grid grid-cols-4 gap-3 [&_b]:text-ink-gray-4 [&_b]:font-normal text-sm -mt-1"
		>
			<div class="flex flex-col gap-2 border p-4 rounded ">
				<b> Created by </b>
				<span class="text-ink-gray-9"
					>{{ deployview ?  builds[activeBuildId]?.doc?.owner : pipeline?.doc?.owner }}
				</span>
			</div>

			<div class="flex flex-col gap-2 border p-4 rounded">
				<b> Start </b>
				<span>
					{{ date(deployview ?  builds[activeBuildId]?.doc?.build_start : pipeline?.doc?.steps?.start) || '-' }}
				</span>
			</div>

			<div class="flex flex-col gap-2 border p-4 rounded">
				<b> End </b>
				<span>
					{{ date(deployview ?  builds[activeBuildId]?.doc?.build_end : pipeline?.doc?.steps?.end) || '-' }}
				</span>
			</div>

			<div class="flex flex-col gap-2 border p-4 rounded">
				<b> Duration </b>
				<span>
					{{ deployview ? duration( builds[activeBuildId]?.doc?.build_duration) || '-' : secsToDuration(pipeline?.doc?.steps?.duration) || '-' }}
				</span>
			</div>
		</section>

		<!-- deploy steps + output -->
		<div
			class="flex rounded border p-3 pt-1 flex-1 min-h-0"
			:class='output.val? "": "!pr-0" '
		>
			<Scrollbar
				class="px-0.5 pr-3 transition-all duration-500 shrink-0"
				:class="output.val ? 'w-[30rem]' : 'w-full'"
			>
				<Tabs
					class="w-full sticky top-0 z-10 bg-surface-white mb-2"
					tablistClass="!px-0"
					:tabs="sidebarTabs"
					v-model="tabState"
				>
					<template #suffix="{ tab }">
						<span
							v-if='tab.label == "Issues"'
							class="bg-surface-gray-2 py-0.5 px-1 rounded text-xs leading-none"
						>
							{{ (errors?.data?.length || 0) + (warnings?.data?.length || 0) }}</span
						>
					</template>
				</Tabs>

				<!-- build stages -->
				<template v-if='tabState == "Tasks"'>
					<template
						v-for='x in (deployview ? dummyStages : pipeline?.doc?.steps?.stages)'
						:key="x.label"
					>
						<Collapsable
							v-if="x.label == 'Building'"
							headerCss="py-3 border-b"
							:disabled='["Pending", "Queued"].includes(x.status)'
						>
							<template #header>
								<StatusIcon :status="x.status" />
								<span class="whitespace-nowrap"> {{ x.label }}</span>
							</template>

							<!-- build steps -->
							<template v-if='x.label == "Building"'>
								<button
									v-for="(build_step, step_i) in builds[activeBuildId]?.doc?.build_steps"
									class="leading-relaxed mb-0.5 py-1.5 pr-3 pl-6 rounded flex items-center gap-2 justify-start whitespace-nowrap w-full disabled:opacity-70 disabled:cursor-not-allowed hover:bg-surface-gray-1"
									:class='output.val && output.selectedIndex == step_i? "bg-surface-gray-1" :"" '
									@click="setOutput({ val: build_step.output || formatCmd(build_step.command) || 'No Output', status: build_step.status, selectedIndex: step_i })"
									:disabled="build_step.status =='Pending'"
								>
									<StatusIcon :status="build_step.status" />
									<span class="mr-3">
										{{ build_step.stage }}
										- {{ build_step.step }}
									</span>
									<span class="text-ink-gray-5 ml-auto"
										>{{ build_step.cached ? 'Cached': secsToDuration(build_step.duration) }}</span
									>
								</button>
							</template>
						</Collapsable>

						<div v-else class="flex items-center gap-2 py-3 border-b">
							<StatusIcon :status="x.status" />
							<span class="whitespace-nowrap"> {{ x.label }}</span>
							<span
								v-if='x.status != "Failure"'
								class="ml-auto text-sm text-ink-gray-5"
							>
								{{ secsToDuration(x.duration) }}
							</span>
						</div>
					</template>
				</template>

				<!-- list of errors -->
				<template v-else>
					<div
						v-for='x in [...errors?.data || [], ...warnings?.data || []]?.filter(x => x.document_name == activeBuildId)'
						class="flex flex-col gap-1"
					>
						<Collapsable headerCss="py-3" class="mb-3">
							<template #header>
								<StatusIcon
									:status="x.class == 'Error' ? 'Failed' : 'Warning'"
								/>
								{{ x.title }}
								{{ x.class }}
							</template>

							<div class="rounded p-3 bg-surface-red-1 flex flex-col gap-2">
								<p
									v-html="x.message"
									class="!w-full !max-w-full  prose prose-sm ml-3 mb-3 text-sm"
									:class='x.class == "Error" ? " bg-surface-red-1 text-ink-red-4" : "bg-surface-amber-1 text-ink-amber-3"'
								/>

								<a
									:href="x.assistance_url"
									v-if="x.assistance_url"
									target="_blank"
									class="bg-surface-white shadow p-1.5 px-2.5 rounded hover:opacity-70 ml-auto"
								>
									Go to docs
								</a>
							</div>
						</Collapsable>
					</div>
				</template>
			</Scrollbar>

			<!-- output -->
			<div
				v-show="output.val"
				class="overflow-hidden bg-surface-gray-1 dark:bg-surface-cards p-3 mt-2 rounded transition-all duration-500 flex-1"
			>
				<div
					class="flex items-center gap-2 pb-2 border-outline-gray-2 mb-3 text-ink-gray-6"
				>
					<span>Output</span>
					<CopyBtn :text="output?.val || ''" class="ml-auto" />
					<button @click="setOutput({ val: null, status: null })">
						<lucide-x class="size-4" />
					</button>
				</div>

				<pre
					class="font-mono text-xs overflow-auto -m-3 p-1 px-3.5"
					:class='output.status == "Failure" ? "bg-surface-red-1 text-ink-red-3" :
          ""'
				>{{ output.val }}</pre>
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
