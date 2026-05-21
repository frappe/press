<script setup lang="ts">
import { getCachedDocumentResource, createDocumentResource } from 'frappe-ui'
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'

import { date, secsToDuration } from '@/utils/format'
import { watch, ref, inject, onBeforeUnmount } from 'vue'

const setOutput = inject('setOutput')
const output = inject('output')

interface Props {
	stages: any
	buildIds: String[]
	activeBuildId: String | null
  updateDummyStage?: any
  updateDeployViewBuild? :any
  deployview?: boolean
}

const props = defineProps<Props>()

// used to unsubscribe from socket events
const wired = new Set<string>()

const buildResources = ref<Record<string, any>>({})
const socket = window.$socket

const handleDummyStage = (x) => {
  if(!props.deployview)  return

  props.updateDeployViewBuild(x)
  props.updateDummyStage(2, x.status)
  props.updateDummyStage(3, x.status == 'Success' ? x.status: 'Pending')
}

watch(
	() => props.buildIds,
	(ids) => {
		if (!ids?.length) return

		ids.forEach((id) => {
			if (!buildResources.value[id]) {

				buildResources.value[id] = createDocumentResource({
					doctype: 'Deploy Candidate Build',
					name: id,
					auto: true,
					fields: ['build_steps'],
          onSuccess: handleDummyStage
				})

         if (buildResources.value[id]?.doc) {
             handleDummyStage(buildResources.value[id].doc)
         }
			}

			// socket io stuff
			if (socket && !wired.has(id)) {
				socket.emit('doc_subscribe', 'Deploy Candidate Build', id)

				socket.on(`bench_deploy:${id}:steps`, (data) => {
					const buildRes = buildResources.value[id]
					if (data.name === id && buildRes) {
						buildRes.doc.build_steps = data.steps
					}
				})

				socket.on(`bench_deploy:${id}:finished`, () => {
					buildResources.value[id]?.reload()

         if(props.updateDummyStage) {
            props.updateDummyStage(2, "Success")
            props.updateDummyStage(3, "Success")
         }

					const rgDoc = getCachedDocumentResource(
						'Release Group',
						buildResources.value[id]?.doc?.group,
					)
					if (rgDoc) rgDoc.reload()

					// this.$resources.deploy.reload();
					// this.$resources.errors.reload();
					// this.$resources.warnings.reload();
				})
			}

			wired.add(id)
		})
	},
	{ immediate: true, deep: true },
)

onBeforeUnmount(() => {
	const socket = window.$socket

	wired.forEach((id) => {
		socket.emit('doc_unsubscribe', 'Deploy Candidate Build', id)
		socket.off(`bench_deploy:${id}:steps`)
	})
})

// single line commands with && are very long
// so make them long
const formatCmd = (cmd: string) => {
	return cmd
		.split('&&')
		.map((part) => part.trim())
		.join(' &&\n')
}


</script>

<template>
	<Collapsable
		v-for='(x, i) in stages'
		:headerCss="`${i == stages.length-1 ? '':'border-b'} py-3`"
		:key="x.label"
		:disabled='["Pending", "Queued"].includes(x.status)'
	>
		<template #header>
			<StatusIcon :status="x.status" />
			<span class="whitespace-nowrap"> {{ x.label }}</span>
		</template>

		<div class="my-2 *:leading-relaxed text-sm" v-if='x.label == "Building"'>
			<button
				v-for="build_step, step_i in buildResources[activeBuildId]?.doc?.build_steps"
				class="py-1.5 pr-3 pl-6 rounded flex items-center gap-2 justify-start whitespace-nowrap w-full disabled:opacity-70 disabled:cursor-not-allowed hover:bg-surface-gray-1"
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
		</div>

		<!-- steps other than 2 have no output so show some data-->
		<div v-else class="flex" :class='output.val? "flex-col" : "flex-row"'>
			<div class="flex flex-col gap-2 p-3">
				<span class="text-sm font-medium text-ink-gray-4"> Start </span>
				<span class="text-sm text-ink-gray-9"> {{ date(x.start) }} </span>
			</div>

			<div class="flex flex-col gap-2 p-3">
				<span class="text-sm font-medium text-ink-gray-4"> End </span>
				<span class="text-sm text-ink-gray-9"> {{ date(x.end) }} </span>
			</div>

			<div class="flex flex-col gap-2 p-3">
				<span class="text-sm font-medium text-ink-gray-4"> Duration </span>
				<span class="text-sm text-ink-gray-9">
					{{ secsToDuration(x.duration) }}
				</span>
			</div>
		</div>
	</Collapsable>
</template>
