<template>
	<CardDetails :showDetails="job">
		<div class="px-6 py-5">
			<template v-if="job">
				<div class="flex items-center">
					<Button
						class="mr-3 md:hidden"
						@click="$router.back()"
						icon="chevron-left"
					/>
					<div>
						<h4 class="text-lg font-medium">
							{{ job.job_type }}
						</h4>
						<p class="mt-1 text-sm text-gray-500">
							<template v-if="job.status === 'Success'">
								Completed
								<FormatDate type="relative">
									{{ job.creation }}
								</FormatDate>
								in {{ formatDuration(job.duration) }}
							</template>
							<template v-if="job.status === 'Undelivered'">
								Job failed to start
							</template>
						</p>
					</div>
				</div>
			</template>
			<div v-else>
				<Button
					:loading="true"
					loading-text="Loading..."
					v-if="$resources.job.loading"
				/>
				<span v-else class="text-base text-gray-600">
					{{ jobName ? 'Invalid Job' : 'No job selected' }}
				</span>
			</div>
		</div>
		<div class="flex-auto overflow-auto" v-if="job">
			<details
				class="px-6 cursor-pointer"
				v-for="(step, index) in job.steps"
				:key="step.step_name"
			>
				<summary
					class="inline-flex items-center py-2 text-xs text-gray-600 focus:outline-none"
				>
					<span class="ml-1">
						<Spinner v-if="isStepRunning(step)" class="w-3 h-3 text-gray-500" />
						<div
							v-if="step.status"
							class="grid w-4 h-4 border rounded-full place-items-center"
							:class="{
								'border-green-500 bg-green-50': isStepCompleted(step, index),
								'border-red-500 bg-red-50': step.status === 'Failure',
								'border-gray-500 bg-gray-50': step.status === 'Skipped'
							}"
						>
							<FeatherIcon
								:name="
									// prettier-ignore
									isStepCompleted(step, index)
										? 'check'
										: step.status === 'Failure'
											? 'x'
											: step.status === 'Skipped'
												? 'minus'
												: 'slash'
								"
								:class="{
									'text-green-500': isStepCompleted(step, index),
									'text-red-500': step.status === 'Failure',
									'text-gray-500': step.status === 'Skipped'
								}"
								:stroke-width="3"
								class="w-3 h-3"
							/>
						</div>
					</span>
					<span class="ml-2 text-sm font-medium text-gray-900 select-none">
						{{ step.step_name }}
					</span>
				</summary>
				<div :class="index == job.steps.length - 1 ? 'pb-4' : 'pb-2'">
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
	name: 'SiteJobsDetail',
	props: ['jobName'],
	components: { CardDetails },
	inject: ['viewportWidth'],
	resources: {
		job() {
			return {
				method: 'press.api.site.job',
				params: {
					job: this.jobName
				},
				auto: Boolean(this.jobName)
			};
		}
	},
	computed: {
		job() {
			return this.$resources.job.data;
		}
	},
	methods: {
		formatDuration(duration) {
			return duration.split('.')[0];
		},
		isStepRunning(step) {
			if (this.jobName !== this.runningJob?.id) return false;
			let runningStep = this.runningJob.steps.find(
				s => s.name == step.step_name
			);
			return runningStep?.status === 'Running';
		},
		isStepCompleted(step, index) {
			if (this.jobName === this.runningJob?.id) {
				return this.runningJob.current.index > index;
			}
			return step.status === 'Success';
		}
	}
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
	height: 12px;
}

details[open] > summary::before {
	content: url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 12 12' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.5 4.25L6 7.75L9.5 4.25' stroke='%231F272E' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E%0A");
	height: 12px;
}
</style>
