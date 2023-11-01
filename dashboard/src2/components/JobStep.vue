<template>
	<div>
		<button
			class="flex w-full items-center justify-between rounded bg-gray-50 px-2.5 py-2 text-left text-base"
			@click="step.isOpen = !step.isOpen"
			:class="step.isOpen ? 'rounded-b-none' : ''"
		>
			<div class="flex items-center space-x-2">
				<Tooltip :text="step.status">
					<div
						class="grid h-4 w-4 place-items-center rounded-full"
						:class="{
							'bg-green-500': step.status === 'Success',
							'bg-red-500': step.status === 'Failure',
							'bg-gray-400': ['Skipped', 'Running', 'Pending'].includes(
								step.status
							)
						}"
					>
						<FeatherIcon
							:name="
								{
									Success: 'check',
									Failure: 'x',
									Skipped: 'minus',
									Running: 'clock',
									Pending: 'clock'
								}[step.status]
							"
							class="h-3 w-3 text-white"
							:stroke-width="3"
						/>
					</div>
				</Tooltip>
				<span>
					{{ step.title }}
				</span>
			</div>

			<div class="text-gray-600" v-if="step.duration">
				{{ step.duration }}
			</div>
		</button>
		<div
			class="overflow-x-auto border px-2.5 py-2 text-sm text-gray-800"
			v-show="step.isOpen"
		>
			<pre>{{ step.output || 'No output' }}</pre>
		</div>
	</div>
</template>
<script setup>
const props = defineProps({
	step: {
		type: Object,
		required: true
	}
});
</script>
