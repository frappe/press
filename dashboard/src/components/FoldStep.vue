<template>
	<div>
		<button
			class="flex w-full items-center justify-between rounded bg-surface-gray-1 px-2.5 py-2 text-left text-base"
			@click="$emit('toggle')"
			:class="open ? 'rounded-b-none' : ''"
		>
			<div class="flex items-center space-x-2">
				<span
					:class="[open || status == 'Running' ? 'lucide-chevron-down' : 'lucide-chevron-right', 'h-3 w-3 text-ink-gray-6']"
				/>
				<Tooltip :text="status">
					<div
						class="grid h-4 w-4 place-items-center rounded-full"
						:class="iconClass"
					>
						<LoadingIndicator
							class="h-3.5 w-3.5 text-ink-gray-9"
							v-if="status === 'Running'"
						/>
						<span :class="[icon, 'h-3 w-3 text-white']" v-else />
					</div>
				</Tooltip>
				<span> {{ title }} </span>
			</div>

			<div class="text-ink-gray-6" v-if="caption">
				{{ caption }}
			</div>
		</button>
		<div
			class="overflow-auto py-2 px-2.5 text-sm bg-surface-gray-3 rounded-b border border-outline-gray-1"
			v-show="open || status == 'Running'"
			ref="output"
		>
			<pre class="max-h-[50vh]">{{ body }}</pre>
		</div>
	</div>
</template>
<script lang="ts">
import { LoadingIndicator } from 'frappe-ui'
import { defineComponent } from 'vue'

export default defineComponent({
	name: 'FoldStep',
	props: {
		open: { type: Boolean, required: true },
		title: { type: String, required: true },
		body: { type: String, required: true },
		status: { type: String, required: false },
		caption: { type: String, required: false },
	},
	emits: ['toggle'],
	watch: {
		body(val, oldVal) {
			if (val === oldVal) {
				return
			}

			this.$nextTick(() => {
				this.$refs.output.scrollTop = this.$refs.output.scrollHeight
			})
		},
	},
	computed: {
		icon(): string {
			switch (this.status) {
				case 'Success':
					return 'lucide-check'
				case 'Failure':
					return 'lucide-x'
				case 'Delivery Failure':
					return 'lucide-x'
				case 'Pending':
					return 'lucide-clock'
				case 'Skipped':
					return 'lucide-minus'
				default:
					return 'lucide-circle'
			}
		},
		iconClass(): string {
			switch (this.status) {
				case 'Success':
					return 'bg-green-500'
				case 'Failure':
					return 'bg-red-500'
				case 'Delivery Failure':
					return 'bg-red-500'
				case 'Running':
					return 'bg-transparent'
				default:
					return 'bg-surface-gray-4'
			}
		},
	},
})
</script>
