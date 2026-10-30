<template>
	<ol class="flex items-center gap-2 text-sm">
		<template v-for="(step, i) in steps" :key="step">
			<li
				class="flex items-center gap-1.5"
				:class="i <= current ? 'text-ink-gray-9' : 'text-ink-gray-5'"
			>
				<span
					class="flex h-5 w-5 items-center justify-center rounded-full"
					:class="i < current || isComplete ? 'bg-surface-gray-7 text-ink-white' : i === current ? 'border-2 border-outline-gray-5' : 'border border-outline-gray-3'"
				>
					<LucideCheck v-if="i < current || isComplete" class="h-3 w-3" />
				</span>
				{{ step }}
			</li>
			<li
				v-if="i < steps.length - 1"
				class="h-px flex-1 bg-outline-gray-2"
				aria-hidden="true"
			/>
		</template>
	</ol>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, required: true } })

const steps = ['Order placed', 'Payment received', 'Signed by Frappe', 'Active']
const progress = {
	'Awaiting Payment': 1,
	'Pending Signature': 2,
	Active: 3,
}

const current = computed(() => progress[props.status] ?? 0)
const isComplete = computed(() => props.status === 'Active')
</script>
