<script setup lang="ts">
import Collapsable from '@/components/common/Collapsable.vue'
import { duration, secsToDuration } from '@/utils/format'
import StatusIcon from './StatusIcon.vue'
import { Spinner } from 'frappe-ui'

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
// const formatCmd = (cmd: string) => {
// 	return cmd
// 		.split('&&')
// 		.map((part) => part.trim())
// 		.join(' &&\n')
// }

const isStageDisabled = (x) => {
	if (['Pending', 'Queued'].includes(x.status)) return true

	if (
		x.label == 'Building' &&
		(props.buildSteps?.length == 0 || !props.buildSteps)
	)
		return true

	if (x.label == 'Deploying' && x.benches?.length == 0) return true

	return false
}
</script>

<template>
	<div
		v-if="!stages || stages?.length ==0"
		class="leading-relaxed py-2.5 text-ink-gray-5 flex flex-wrap sk-fade"
	>
		<div class="flex  items-center gap-2 text-sm pb-3 w-full border-b">
			<Spinner class="size-4" />
			<span>Deploy is queued and will start shortly...</span>
		</div>

		<div
			v-for="i in 3"
			:key="i"
			class="flex items-center gap-3 py-3 border-b border-surface-gray-2 w-full"
		>
			<div class="animate-pulse rounded size-4 bg-surface-gray-3 shrink-0" />

			<div
				class="animate-pulse rounded h-3.5 bg-surface-gray-3"
				:style="{ width: i % 2 === 0 ? '140px' : '180px' }"
			/>

			<div class="flex-1" />

			<div
				class="animate-pulse rounded h-3.5 bg-surface-gray-3"
				:style="{ width: i <= 1 ? '24px' : '16px' }"
			/>
		</div>
	</div>

	<template v-for='(x, i) in stages' :key="x.name" v-else>
		<Collapsable
			v-if="x.label === 'Building' || (!deployview && x.label === 'Deploying')"
			:headerCss="`py-3 pr-2  ${i != stages?.length-1?'aria-[expanded=false]:border-b': '' }`"
			:disabled="isStageDisabled(x)"
			:opened="x.status === 'Running' && (x.label === 'Building' || x.label === 'Deploying')"
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
					:data-step-id="build_step.name"
					@click="setOutput({ val: build_step.output,
                  status: build_step.status, id: build_step.name })"
					:disabled="build_step.status =='Pending'"
				>
					<StatusIcon :status="build_step.status" />
					<span class="mr-3 truncate">
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

					<!-- Only first job "New Bench" is useful so use it only-->
					<template v-if="bench.jobs?.length">
						<button
							class="btn !pl-12"
							v-for="jobstep in agentJobs?.[bench.jobs[0].name]?.doc?.steps"
							:key="jobstep.name"
							:aria-selected="output?.val && output?.id == jobstep.name"
							@click="setOutput({     val: jobstep.output,
      status: jobstep.status,
      id: jobstep.name
    })"
						>
							<StatusIcon :status="jobstep.status" class="ml-2" />
							{{ jobstep.step_name }}

							<span class="text-ink-gray-5 ml-auto pr-1">
								{{ duration(jobstep.duration) }}
							</span>
						</button>
					</template>
				</Collapsable>
			</template>
		</Collapsable>

		<div v-else class="flex items-center gap-2 py-3 border-b">
			<StatusIcon :status="x.status" />
			<span class="whitespace-nowrap"> {{ x.label }}</span>
			<span v-if="x.duration" class="ml-auto text-sm text-ink-gray-5 pr-2">
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

.sk-fade {
	animation: sk-fade-in 0.25s ease-out both;
}

@keyframes sk-fade-in {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}
</style>
