<script setup lang="ts">
<<<<<<< HEAD
<<<<<<< HEAD
import { getCachedDocumentResource, createDocumentResource } from 'frappe-ui'
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'

import { date, secsToDuration } from '@/utils/format'
import { watch, ref, inject, onMounted, onBeforeUnmount } from 'vue'
=======
import { createResource, createDocumentResource } from 'frappe-ui'
=======
import { getCachedDocumentResource, createDocumentResource } from 'frappe-ui'
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'

import { date, secsToDuration } from '@/utils/format'
<<<<<<< HEAD
import { watch, ref, computed, inject } from 'vue'
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
import { watch, ref, inject, onMounted, onBeforeUnmount } from 'vue'
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)

const setOutput = inject('setOutput')
const output = inject('output')

interface Props {
	stages: any
	buildIds: String[]
<<<<<<< HEAD
<<<<<<< HEAD
	activeBuildId: String
=======
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
	activeBuildId: String
>>>>>>> b75bf0a79 (feat(new-deploy-flow): support multiple builds)
}

const props = defineProps<Props>()

<<<<<<< HEAD
<<<<<<< HEAD
// used to unsubscribe from socket events
const wired = new Set<string>()

const buildResources = ref<Record<string, any>>({})
const socket = window.$socket

watch(
	() => props.buildIds,
=======
=======
// used to unsubscribe from socket events
const wired = new Set<string>()

>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
const buildResources = ref<Record<string, any>>({})
const socket = window.$socket

watch(
<<<<<<< HEAD
	() => props.buildIds.slice(),
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
	() => props.buildIds,
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
	(ids) => {
		if (!ids?.length) return

		ids.forEach((id) => {
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
			if (!buildResources.value[id]) {
				buildResources.value[id] = createDocumentResource({
					doctype: 'Deploy Candidate Build',
					name: id,
					auto: true,
					fields: ['build_steps'],
				})
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
<<<<<<< HEAD
<<<<<<< HEAD
					buildResources.value[id]?.reload()

=======
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
=======
					buildResources.value[id]?.reload()

>>>>>>> 23ef75d55 (fix(deploy-ui): add missing resource.reload() on bench steps finish)
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
<<<<<<< HEAD
=======
			buildResources.value[id] = createDocumentResource({
				doctype: 'Deploy Candidate Build',
				name: id,
				auto: true,
				fields: ['build_steps'],
			})
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
		})
	},
	{ immediate: true, deep: true },
)

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
onBeforeUnmount(() => {
	const socket = window.$socket

	wired.forEach((id) => {
		socket.emit('doc_unsubscribe', 'Deploy Candidate Build', id)
		socket.off(`bench_deploy:${id}:steps`)
	})
})

// single line commands with && are very long
// so make them long
<<<<<<< HEAD
=======
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
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
<<<<<<< HEAD
<<<<<<< HEAD
		:disabled='["Pending", "Queued"].includes(x.status)'
=======
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
		:disabled='["Pending", "Queued"].includes(x.status)'
>>>>>>> dddcb986e (fix(deploy-ui): disable steps if they are pending)
	>
		<template #header>
			<StatusIcon :status="x.status" />
			<span class="whitespace-nowrap"> {{ x.label }}</span>
		</template>

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> e6ff3635e (fix(new-deploy-ui): show multiple build architechture in tab ui)
		<div class="ml-6 my-1" v-if='x.label == "Building"'>
			<button
				v-for="build_step in buildResources[activeBuildId]?.doc?.build_steps"
				class="py-2 flex items-center gap-2 justify-start whitespace-nowrap w-full disabled:opacity-70 disabled:cursor-not-allowed"
				@click="setOutput(build_step.output || formatCmd(build_step.command) || 'No Output') "
				:disabled="build_step.status =='Pending'"
			>
				<StatusIcon :status="build_step.status" />
				<span class="mr-3">
					{{ build_step.stage }}
					- {{ build_step.step }}
				</span>
				<span class="text-ink-gray-5 ml-auto"
					>{{ build_step.cached ? 'Cached': secsToDuration(build_step.duration) }}</span
=======
		<div class="ml-6 my-3" v-if='x.label == "Building"'>
			<button
				v-for="build_step in buildResources[activeBuildId]?.doc?.build_steps"
				class="py-2 flex items-center gap-2 justify-start whitespace-nowrap w-full disabled:opacity-70 disabled:cursor-not-allowed"
				@click="setOutput(build_step.output || formatCmd(build_step.command) || 'No Output') "
				:disabled="build_step.status =='Pending'"
			>
				<StatusIcon :status="build_step.status" />
				<span class="mr-3">
					{{ build_step.stage }}
					- {{ build_step.step }}
				</span>
				<span class="text-ink-gray-5 ml-auto"
<<<<<<< HEAD
					>{{ build_step.cached ? 'Cached': build_step.duration }}</span
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
					>{{ build_step.cached ? 'Cached': secsToDuration(build_step.duration) }}</span
>>>>>>> f3d59bb40 (fix(format): add missing secsToDuration())
				>
			</button>
		</div>

		<!-- steps other than 2 have no output so show some data-->
<<<<<<< HEAD
<<<<<<< HEAD
		<div v-else class="flex" :class='output? "flex-col" : "flex-row"'>
=======
		<div v-else class="flex flex-col" :class='output? "" : "flex-row"'>
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
		<div v-else class="flex" :class='output? "flex-col" : "flex-row"'>
>>>>>>> f3d59bb40 (fix(format): add missing secsToDuration())
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
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
				<span class="text-sm text-ink-gray-9">
					{{ secsToDuration(x.duration) }}
				</span>
=======
				<span class="text-sm text-ink-gray-9"> {{ x.duration }} </span>
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
				<span class="text-sm text-ink-gray-9"> {{ secsToDuration(x.duration) }} </span>
>>>>>>> f3d59bb40 (fix(format): add missing secsToDuration())
=======
				<span class="text-sm text-ink-gray-9">
					{{ secsToDuration(x.duration) }}
				</span>
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
			</div>
		</div>
	</Collapsable>
</template>
