<script setup lang="ts">
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'

import { secsToDuration, duration } from '@/utils/format'

interface Props {
	stages: any
	buildSteps: any[]
	agentJobs: any[]
	output: any
	setOutput: any
	deployview: boolean
}

const props = defineProps<Props>()

// single line commands with && are very long
// so make them multi-line
const formatCmd = (cmd: string) => {
	return cmd
		.split('&&')
		.map((part) => part.trim())
		.join(' &&\n')
}
</script>

<template>
	<template v-for='(x, i) in stages' :key="x.name">
		<Collapsable
			v-if="deployview ? x.label == 'Building' : ['Building', 'Deploying'].includes(x.label)"
			:headerCss="`py-3 pr-2  ${i != stages?.length-1?'aria-[expanded=false]:border-b': '' }`"
			:disabled='["Pending", "Queued"].includes(x.status)'
		>
			<template #prefix>
				<StatusIcon :status="x.status" />
				<span class="whitespace-nowrap"> {{ x.label }}</span>
			</template>

			<!-- build steps -->
			<template v-if='x.label == "Building"'>
				<button
					v-for="(build_step) in buildSteps"
					class="btn !pl-6 !pr-2"
					:aria-selected="output?.val && output?.id == build_step.name"
					@click="setOutput({ val: build_step.output || formatCmd(build_step.command),
                  status: build_step.status, id: build_step.name })"
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
				<hr class="mt-1" />
			</template>

			<template v-else-if='!deployview && x.label == "Deploying"'>
				<Collapsable
					v-for='bench in x.benches'
					headerCss="ml-6 py-2 pr-2 -mt-1"
					:key="bench.name"
					:opened="true"
				>
					<template #prefix>
						<LucideBoxes class="size-4 shrink-0" />
						{{ bench.name }}
						<span class="text-ink-gray-5 mx-1">|</span>
						<LucideServer class="size-4 text-ink-gray-5 shrink-0" />
						<span class="text-ink-gray-5">
							{{ bench.server?.split('.')?.[0] }}
						</span>
					</template>

					<Collapsable
						:opened="true"
						v-for='job in bench.jobs'
						headerCss="ml-12 py-2 pr-2"
						:key="job.name"
					>
						<template #prefix>
							<LucideBox class="size-4" />
							{{ job.job_type }}
						</template>

						<button
							class="btn !pl-16"
							:aria-selected="output?.val && output?.id == jobstep.name"
							:key="jobstep.name"
							v-for='jobstep in agentJobs?.[job.name]?.doc?.steps'
							@click="setOutput({val: jobstep.output, status: jobstep.status, id: jobstep.name})"
						>
							<StatusIcon :status="jobstep.status" class="ml-2" />
							{{ jobstep.step_name }}

							<span class="text-ink-gray-5 ml-auto pr-1">
								{{ duration(jobstep.duration) }}</span
							>
						</button>
					</Collapsable>
				</Collapsable>
			</template>
		</Collapsable>

		<div v-else class="flex items-center gap-2 py-3 border-b">
			<StatusIcon :status="x.status" />
			<span class="whitespace-nowrap"> {{ x.label }}</span>
			<span
				v-if='x.status != "Failure"'
				class="ml-auto text-sm text-ink-gray-5 pr-2"
			>
				{{ secsToDuration(x.duration) }}
			</span>
		</div>
	</template>
</template>

<style scoped>
.btn {
	@apply leading-relaxed mb-0.5 p-1 aria-selected:bg-surface-gray-1;
	@apply rounded flex items-center gap-2 justify-start whitespace-nowrap w-full;
	@apply disabled:opacity-70 disabled:cursor-not-allowed hover:bg-surface-gray-1;
}
</style>
