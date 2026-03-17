<script setup lang="ts">
import { ref } from 'vue';
import LucideChevronRight from '~icons/lucide/chevron-right';
import LucideClock from '~icons/lucide/clock';
import LucideCheck from '~icons/lucide/circle-check';
import LucideZap from '~icons/lucide/zap';
import LucideServer from '~icons/lucide/server';
import LucideDatabase from '~icons/lucide/database';
import LucideBan from '~icons/lucide/ban';
import LucideAlert from '~icons/lucide/alert-triangle';
import LucideWrench from '~icons/lucide/wrench';
import { Badge } from 'frappe-ui';

const statusClasses = {
	Resolved: 'green',
	Validating: 'orange',
	Confirming: 'orange',
	default: 'red',
};
const timelineDotClasses = {
	Created: 'text-ink-gray-6',
	Confirmed: 'text-ink-amber-3',
	Resolved: 'text-ink-green-2',
};
const actionStatusClasses = {
	Success: 'text-ink-green-2',
	Failure: 'text-ink-red-3',
	Pending: 'text-ink-amber-3',
	default: 'text-ink-gray-5',
};

interface Props {
	data: any;
}

const props = defineProps<Props>();

const toggled = ref(true);
const toggleIncident = () => (toggled.value = !toggled.value);
</script>

<template>
	<div
		class="mb-5 overflow-hidden rounded-lg border border-outline-gray-1 bg-surface-cards transition-all"
	>
		<!-- Card header & toggle btn -->
		<button
			class="w-full flex cursor-pointer items-center gap-2.5 p-3 hover:bg-surface-gray-1 transition-colors truncate text-sm font-medium text-ink-gray-9"
			@click="toggleIncident"
		>
			<LucideChevronRight
				class="size-4 shrink-0 text-ink-gray-6 transition-transform duration-200"
				:class="{ 'rotate-90': !toggled }"
			/>

			{{ data.server }}

			<Badge
				:label="data.status"
				:theme="statusClasses[data.status]"
				class="ml-auto"
			>
				<template #prefix>
					<div class="size-1.5 rounded-full r-1 bg-current opacity-80" />
				</template>
			</Badge>
		</button>

		<!-- Card body -->
		<div v-if="!toggled" class="border-t border-outline-gray-2 px-4 pb-4">
			<!-- Timeline -->
			<div v-if="data.timelineSteps.length" class="mt-3">
				<div class="mb-2 flex items-center gap-2.5">
					<LucideClock class="size-3.5" />
					<span
						class="text-sm font-semibold uppercase tracking-widest text-ink-gray-6"
						>Timeline</span
					>
				</div>

				<div class="flex flex-col">
					<div
						v-for="(step, idx) in data.timelineSteps"
						:key="idx"
						class="relative flex items-center gap-3 py-1.5"
					>
						<LucideCheck
							class="size-3.5"
							:class="[
								timelineDotClasses[step.label] || 'border-outline-gray-3',
							]"
						/>
						<span class="flex-1 text-sm font-medium text-ink-gray-7">{{
							step.label
						}}</span>
						<span class="text-sm text-ink-gray-5">{{ step.time }}</span>
					</div>
				</div>
			</div>

			<!-- Investigation -->
			<div v-if="data.investigation" class="mt-4">
				<div class="mb-4 flex items-center gap-1.5">
					<LucideZap class="size-3.5" />
					<span class="text-sm font-semibold uppercase tracking-widest"
						>Investigation</span
					>
				</div>

				<div class="rounded-lg bg-surface-gray-1 px-4 py-3">
					<div class="mb-2.5 flex items-center justify-between">
						<span class="text-sm font-medium text-ink-gray-9">{{
							data.investigation.name
						}}</span>
						<Badge :label="data.investigation.status" variant="solid" />
					</div>

					<div
						v-for="group in data.investigation.groups"
						:key="group.label"
						class="mb-4 last:mb-0"
					>
						<div
							class="mb-2 flex items-center gap-1.5 border-b border-outline-gray-2 pb-2"
						>
							<LucideServer v-if="group.label === 'Server'" class="size-3" />
							<LucideDatabase v-else class="size-3" />
							<span class="text-sm font-semibold">{{ group.label }}</span>
						</div>

						<div
							v-for="(step, idx) in group.steps"
							:key="idx"
							class="flex items-center gap-2 py-1"
						>
							<p
								class="min-w-0 flex-1 truncate text-sm font-medium text-ink-gray-8"
							>
								{{ step.step_name }}
							</p>

							<div
								v-if="step.is_unable_to_investigate"
								class="flex items-center gap-1.5 text-ink-gray-5"
							>
								<LucideBan class="size-3" />
								<span class="text-sm">Unable To Investigate</span>
							</div>

							<div
								v-else-if="step.is_likely_cause"
								class="flex shrink-0 items-center gap-1.5 text-ink-amber-3"
							>
								<LucideAlert class="size-3" />
								<span class="text-sm">Likely Cause</span>
							</div>

							<div
								v-else
								class="flex shrink-0 items-center gap-1 text-ink-green-2"
							>
								<LucideCheck class="size-3" />
								<span class="text-sm">Passed</span>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Action steps -->
			<div v-if="data.actionSteps && data.actionSteps.length" class="mt-4">
				<div class="mb-4 flex items-center gap-1.5">
					<LucideWrench class="size-3.5" />
					<span class="text-sm font-semibold uppercase tracking-wiest"
						>Action Taken</span
					>
				</div>

				<div class="flex flex-col gap-1">
					<div
						v-for="(action, idx) in data.actionSteps"
						:key="idx"
						class="flex items-center justify-between rounded-md bg-surface-gray-1 px-3 py-2"
					>
						<span class="truncate text-sm font-medium text-ink-gray-8">{{
							action.label
						}}</span>
						<span
							:class="[
								'ml-3 shrink-0 text-sm font-medium',
								actionStatusClasses[action.status] ||
									actionStatusClasses.default,
							]"
						>
							{{ action.status }}
						</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
