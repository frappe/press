<template>
	<CardDetails :showDetails="showDetails">
		<div class="px-6 py-5">
			<template v-if="showDetails">
				<div class="flex items-center">
					<Button
						class="mr-3 md:hidden"
						@click="$router.back()"
						icon="chevron-left"
					/>
					<div>
						<h4 class="text-lg font-medium">
							{{ title }}
						</h4>
						<p class="mt-1 text-sm text-gray-600" v-if="subtitle">
							{{ subtitle }}
						</p>
					</div>
				</div>
			</template>
			<div v-else>
				<Loading v-if="loading" />
				<span v-else class="text-base text-gray-600"> No item selected </span>
			</div>
		</div>
		<div class="flex-auto overflow-auto" v-if="showDetails">
			<details
				class="px-6 cursor-pointer"
				v-for="(step, index) in steps"
				:key="step.name"
			>
				<summary
					class="inline-flex items-center w-full py-2 focus:outline-none"
				>
					<span class="ml-1">
						<div
							v-if="step.running"
							class="grid w-4 h-4 rounded-full borde place-items-center bg-gray-50"
						>
							<Spinner class="w-3 h-3 text-gray-500" />
						</div>
						<div
							v-else-if="step.status"
							class="grid w-4 h-4 border rounded-full place-items-center"
							:class="{
								'border-green-500 bg-green-50': step.completed,
								'border-red-500 bg-red-50': step.status === 'Failure',
								'border-gray-500 bg-gray-50': step.status === 'Skipped'
							}"
						>
							<FeatherIcon
								:name="
									// prettier-ignore
									step.completed
										? 'check'
										: step.status === 'Failure'
											? 'x'
											: step.status === 'Skipped'
												? 'minus'
												: 'clock'
								"
								:class="{
									'text-green-500': step.completed,
									'text-red-500': step.status === 'Failure',
									'text-gray-500': step.status === 'Skipped'
								}"
								:stroke-width="3"
								class="w-3 h-3"
							/>
						</div>
					</span>
					<span class="ml-2 text-sm font-medium text-gray-900 select-none">
						{{ step.name }}
					</span>
					<div class="ml-auto">
						<span class="text-sm text-gray-600" v-if="step.duration">
							{{ step.duration }}
						</span>
						<component :is="step.action" v-if="step.action" />
					</div>
				</summary>
				<div :class="index == steps.length - 1 ? 'pb-4' : 'pb-2'">
					<div
						class="ml-4 px-2 py-2.5 font-mono text-xs text-gray-900 bg-gray-100 rounded-md"
						:style="{ width: viewportWidth < 768 ? 'calc(100vw - 6rem)' : '' }"
					>
						<div class="overflow-auto">
							<pre>{{ step.output || 'No output' }}</pre>
						</div>
					</div>
				</div>
			</details>
		</div>
	</CardDetails>
</template>
<script>
import CardDetails from '@/components/CardDetails.vue';
export default {
	name: 'StepsDetail',
	props: ['showDetails', 'title', 'subtitle', 'loading', 'steps'],
	components: {
		CardDetails
	},
	inject: ['viewportWidth']
};
</script>

<style scoped>
details > summary {
	list-style-type: none;
}

details > summary::-webkit-details-marker {
	display: none;
}

details > summary::before {
	content: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M4.25 9.5L7.75 6L4.25 2.5' stroke='%231F272E' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
}

details[open] > summary::before {
	content: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.5 4.25L6 7.75L9.5 4.25' stroke='%231F272E' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E%0A");
}
</style>
