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
import Stages from './Stages.vue'
import Loader from './Loader.vue'

import {
	h,
	ref,
	reactive,
	computed,
	watch,
	nextTick,
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
	opened: true,
	val: 'No Output',
	status: null,
	selectedIndex: null,
})
const outputEl = ref<HTMLElement | null>(null)
const stepsEl = ref<HTMLElement | null>(null)

const setOutput = (opts) => {
	output.val = opts.val || 'No Output'
	output.status = opts.status
	output.id = opts.id
	output.opened = opts.opened ?? true
}

const activeBuildId = ref(props.deployview ? props.id : null)
const agentJobs = props.deployview ? null : ref<Record<string, any>>({})
const agentJobIds = props.deployview
	? null
	: computed(() => {
			const benches = pipeline?.doc?.steps?.stages.at(-1)?.benches
			return benches
				?.map((x) => x.jobs)
				.flat()
				.map((x) => x.name)
		})

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
			onSuccess: (data) => {
				const wiredId = 'release-pipeline' + props.id

				if (
					['Pending', 'Running'].includes(data.status) &&
					!wired.has(wiredId)
				) {
					socket.emit('doc_subscribe', 'Release Pipeline', props.id)
					socket.on('doc_update', handleDocUpdate)
					wired.add(wiredId)
				}
			},
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
	onSuccess: () => {
		if (wired?.size > 0 && errList?.value?.length > 0) tabState.value = 'Issues'
	},
}

const errors = createListResource(notifApiFields)
const warnings = createListResource(notifApiFields)

const errList = computed(() => {
	const list = [...(errors?.data || []), ...(warnings?.data || [])]
	const activeErrListId = activeBuildId.value || pipeline?.doc?.name
	return list.filter((x) => x.document_name == activeErrListId)
})

const fetchSetErrs = () => {
	const errids = buildIds.value?.length > 0 ? buildIds.value : [props.id]

	errors.update({
		cache: ['Press Notification Error', 'Deploy Candidate Build', errids],
		filters: { document_name: ['in', errids], class: 'Error' },
	})
	errors.fetch()

	warnings.update({
		cache: ['Press Notification Warning', 'Deploy Candidate Build', errids],
		filters: { document_name: ['in', errids], class: 'Warning' },
	})
	warnings.fetch()
}

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

	dummyStages.value[2].status = x.status

	const pendingState = ['Success', 'Failure'].includes(x.status)
		? x.status
		: 'Pending'
	dummyStages.value[3].status = pendingState
}

const setAutomaticOutput = (steps: any) => {
	const obj = steps.filter((x) => x.status !== 'Pending')?.at(-1)

	if (!obj) return

	output.val = obj.output || 'No Output'
	output.status = obj.status
	output.id = obj.name

	nextTick(() => {
		if (outputEl.value) outputEl.value.scrollTop = outputEl.value.scrollHeight

		const el = stepsEl.value?.querySelector(`[data-step-id="${output?.id}"]`)
		el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
	})
}

watch(
	() => buildIds.value,
	(ids: string[], oldIds: string[]) => {
		if (JSON.stringify(ids) === JSON.stringify(oldIds)) return

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
			if (socket && !wired.has(id) && pipeline?.doc?.status === 'Running') {
				socket.emit('doc_subscribe', 'Deploy Candidate Build', id)

				socket.on(`bench_deploy:${id}:steps`, (data) => {
					const buildRes = builds.value[id]
					if (data.name === id && buildRes) {
						setAutomaticOutput(data.steps)
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

			if (pipeline?.doc?.status === 'Running') wired.add(id)
		})
	},
)

watch(
	() => pipeline?.doc?.status,
	(x) => {
		if (x == 'Failure') fetchSetErrs()
	},
)

watch(
	() => agentJobIds?.value,
	(ids: string[]) => {
		if (props.deployview || !ids) return

		ids.forEach((id: string) => {
			if (!agentJobs.value[id]) {
				agentJobs.value[id] = createDocumentResource({
					doctype: 'Agent Job',
					name: id,
					auto: true,
				})
			}

			if (pipeline?.doc?.status != 'Running') return

			if (socket && !wired.has(`job:${id}`)) {
				socket.emit('doc_subscribe', 'Agent Job', id)

				socket.on('agent_job_update', (data) => {
					if (data.id !== id) return
					const job = agentJobs.value[id]
					if (job?.doc) job.doc = { ...job.doc, ...data }
				})

				wired.add(`job:${id}`)
			}
		})
	},
)

// ---------------------  Realtime stuff ----------------------
const handleDocUpdate = props.deployview
	? null
	: (x) => {
			if (x.doctype === 'Release Pipeline' && x.name === props.id) {
				pipeline.reload()
			}
		}

onBeforeUnmount(() => {
	if (!props.deployview) {
		socket.emit('doc_unsubscribe', 'Release Pipeline', props.id)
		socket.off('doc_update', handleDocUpdate)
		wired.delete('release-pipeline' + props.id)
	}

	wired.forEach((id) => {
		if (id.startsWith('job:')) return

		if (buildIds.value.length == 0) return

		socket.emit('doc_unsubscribe', 'Deploy Candidate Build', id)
		socket.off(`bench_deploy:${id}:steps`)
		socket.off(`bench_deploy:${id}:finished`)
	})

	if (!props.deployview) {
		if (agentJobIds?.value?.length == 0) return

		agentJobIds?.value?.forEach((id: string) => {
			socket.emit('doc_unsubscribe', 'Agent Job', id)
		})

		socket.off('agent_job_update')
	}
})

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
	<Loader
		v-if="deployview? builds[activeBuildId]?.get?.loading: wired.size == 0 && pipeline?.get?.loading"
	/>

	<main
		class="flex flex-col gap-4 py-3 px-5 w-full h-[calc(100dvh-7rem)] mt-1.5"
		v-else
	>
		<!-- header -->
		<div class="flex gap-2 items-center">
			<Button :route="`/groups/${name}/deploys?pipeline=${!deployview}`">
				<template #icon>
					<lucide-chevron-left class="size-4" />
				</template>
			</Button>

			<h2 class="text-ink-gray-9 text-lg font-medium">
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
				size="sm"
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
					<template #icon>
						<lucide-more-horizontal class="size-4" />
					</template>
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
			:class='output.opened? "": "!pr-0" '
			ref="stepsEl"
		>
			<Scrollbar
				class="px-0.5 pr-3 transition-all duration-300 shrink-0"
				:class="output.opened ? 'w-[30rem]' : 'w-full'"
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
							{{ errList?.length || 0 }}</span
						>
					</template>
				</Tabs>

				<!-- build stages -->
				<template v-if='tabState == "Tasks"'>
					<Stages
						:output
						:setOutput
						:stages="deployview ? dummyStages : pipeline?.doc?.steps?.stages"
						:buildSteps="builds[activeBuildId]?.doc?.build_steps"
						:agentJobs="deployview ? null: agentJobs"
						:deployview
					/>
				</template>

				<!-- list of errors -->
				<template v-else>
					<div v-for='x in errList' class="flex flex-col gap-1">
						<Collapsable headerCss="py-3" class="mb-3" opened>
							<template #prefix>
								<StatusIcon
									:status="x.class == 'Error' ? 'Failed' : 'Warning'"
								/>
								{{ x.title }}
								{{ x.class }}
							</template>

							<div
								class="rounded px-3 py-2 bg-surface-red-1 flex flex-col gap-2"
								:class='x.class == "Error" ? " bg-surface-red-1 text-ink-red-4" : "bg-surface-amber-1 text-ink-amber-3"'
							>
								<p v-html="x.message" class="leading-relaxed text-sm" />

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
				v-show="output.opened"
				class="overflow-hidden bg-surface-gray-1 dark:bg-surface-cards p-3 mt-2 rounded transition-all duration-300 flex-1 flex flex-col min-h-0"
			>
				<div
					class="flex items-center pb-2 border-outline-gray-2 mb-3 text-ink-gray-6 -mt-1 -mr-1 shrink-0"
				>
					<span>Output</span>
					<CopyBtn :text="output?.val || ''" class="ml-auto smallbtn" />
					<button
						class="smallbtn"
						@click="setOutput({ val: null, status: null, opened:false })"
					>
						<lucide-x class="size-4" />
					</button>
				</div>

				<pre
					ref="outputEl"
					class="font-mono text-xs overflow-auto -m-3 p-1 px-3.5 flex-1 min-h-0"
					:class='output.status == "Failure" ? "bg-surface-red-1 text-ink-red-3" : ""'
				>{{ output.val }}</pre>
			</div>
		</div>
	</main>
</template>

<style scoped>
.smallbtn {
	@apply hover:bg-surface-gray-3 dark:hover:bg-surface-gray-2 p-1 rounded hover:text-ink-gray-9
}
</style>
