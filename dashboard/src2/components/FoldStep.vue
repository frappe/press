<template>
	<div>
		<button
			class="flex w-full items-center justify-between rounded bg-gray-50 px-2.5 py-2 text-left text-base"
			@click="$emit('toggle')"
			:class="open ? 'rounded-b-none' : ''"
		>
			<div class="flex items-center space-x-2">
				<FeatherIcon
					:name="open ? 'chevron-down' : 'chevron-right'"
					class="h-3 w-3"
					:stroke-width="3"
				/>
				<Tooltip :text="status">
					<div
						class="grid h-4 w-4 place-items-center rounded-full"
						:class="iconClass"
					>
						<LoadingIndicator
							class="h-3.5 w-3.5 text-gray-900"
							v-if="status === 'Running'"
						/>
						<FeatherIcon
							v-else
							:name="icon"
							class="h-3 w-3 text-white"
							:stroke-width="3"
						/>
					</div>
				</Tooltip>
				<span>
					{{ title }}
				</span>
			</div>

			<div class="text-gray-600" v-if="caption">
				{{ caption }}
			</div>
		</button>
		<div
			class="overflow-auto rounded-b border border-gray-100 bg-gray-900 px-2.5 py-2 text-sm text-gray-200"
			v-show="open || status == 'Running'"
			ref="output"
		>
			<pre class="max-h-[50vh]">{{ body }}</pre>
		</div>
	</div>
</template>
<script lang="ts">
import { LoadingIndicator } from 'frappe-ui';
import { defineComponent } from 'vue';

export default defineComponent({
	name: 'FoldStep',
	props: {
		open: { type: Boolean, required: true },
		title: { type: String, required: true },
		body: { type: String, required: true },
		status: { type: String, required: false },
		caption: { type: String, required: false }
	},
	emits: ['toggle'],
	watch: {
		body(val, oldVal) {
			if (val === oldVal) {
				return;
			}

			this.$nextTick(() => {
				this.$refs.output.scrollTop = this.$refs.output.scrollHeight;
			});
		}
	},
	computed: {
		icon(): string {
			switch (this.status) {
				case 'Success':
					return 'check';
				case 'Failure':
					return 'x';
				case 'Pending':
					return 'clock';
				case 'Skipped':
					return 'minus';
				default:
					return 'circle';
			}
		},
		iconClass(): string {
			switch (this.status) {
				case 'Success':
					return 'bg-green-500';
				case 'Failure':
					return 'bg-red-500';
				case 'Running':
					return 'bg-transparent';
				default:
					return 'bg-gray-400';
			}
		}
	}
});
</script>
