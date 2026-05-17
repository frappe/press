<script setup lang="ts">
import { createResource, createDocumentResource } from 'frappe-ui'
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'

import { date } from '@/utils/format'
import { watch, ref, computed, inject } from 'vue'

const setOutput = inject('setOutput')
const output = inject('output')

interface Props {
	stages: any
	buildIds: String[]
}

const props = defineProps<Props>()

const buildResources = ref<Record<string, any>>({})

watch(
	() => props.buildIds.slice(),
	(ids) => {
		if (!ids?.length) return

		ids.forEach((id) => {
			buildResources.value[id] = createDocumentResource({
				doctype: 'Deploy Candidate Build',
				name: id,
				auto: true,
				fields: ['build_steps'],
			})
		})
	},
	{ immediate: true, deep: true },
)

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
	>
		<template #header>
			<StatusIcon :status="x.status" />
			<span class="whitespace-nowrap"> {{ x.label }}</span>
		</template>

		<div class="ml-6 my-3" v-if='x.label == "Building"'>
			<button
				v-for="build_step in buildResources[props.buildIds?.[0]]?.doc?.build_steps"
				class="py-2 flex items-center gap-2 justify-start whitespace-nowrap w-full"
				@click="setOutput(build_step.output || formatCmd(build_step.command) || 'No Output') "
			>
				<StatusIcon :status="build_step.status" />
				<span> {{ build_step.stage }} - {{ build_step.step }} </span>
				<span class="text-ink-gray-5 ml-auto"
					>{{ build_step.cached ? 'Cached': build_step.duration }}</span
				>
			</button>
		</div>

		<!-- steps other than 2 have no output so show some data-->
		<div v-else class="flex flex-col" :class='output? "" : "flex-row"'>
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
				<span class="text-sm text-ink-gray-9"> {{ x.duration }} </span>
			</div>
		</div>
	</Collapsable>
</template>
