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
							'bg-transparent': step.status === 'Running',
							'bg-gray-400': ['Skipped', 'Pending'].includes(step.status)
						}"
					>
						<LoadingIndicator
							class="h-3.5 w-3.5 text-gray-900"
							v-if="step.status === 'Running'"
						/>
						<FeatherIcon
							v-else
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
			class="overflow-auto rounded-b border border-gray-100 bg-gray-900 px-2.5 py-2 text-sm text-gray-200"
			v-show="step.isOpen || step.status == 'Running'"
			ref="output"
		>
			<pre class="max-h-[50vh]">{{ step.output || 'No output' }}</pre>
		</div>
	</div>
</template>
<script>
import { LoadingIndicator } from 'frappe-ui';

export default {
	name: 'JobStep',
	props: {
		step: {
			type: Object,
			required: true
		}
	},
	watch: {
		'step.output': function (val, oldVal) {
			if (val !== oldVal) {
				this.$nextTick(() => {
					this.$refs.output.scrollTop = this.$refs.output.scrollHeight;
				});
			}
		}
	}
};
</script>
