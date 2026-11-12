<template>
	<div class="rounded-md border">
		<div
			v-for="(step, i) in steps"
			:key="i"
			class="flex items-start gap-3 border-b px-5 py-3 text-base last:border-b-0"
		>
			<StatusIcon class="mt-0.5" :status="step.status" />
			<div class="flex-1">
				<div
					:class="step.status === 'Pending' ? 'text-ink-gray-6' : 'text-ink-gray-9'"
				>
					{{ step.title }}
				</div>
				<div v-if="step.description" class="mt-0.5 text-sm text-ink-gray-6">
					{{ step.description }}
				</div>
			</div>
			<div class="shrink-0 text-sm text-ink-gray-6">
				{{ step.date ? formatDate(step.date) : statusText[step.status] }}
			</div>
		</div>
	</div>
</template>

<script setup>
import StatusIcon from '../benches/pipeline/StatusIcon.vue'
import { formatDate } from './format'

defineProps({ steps: { type: Array, required: true } })

const statusText = { Running: 'In progress', Pending: 'Pending', Failed: '' }
</script>
