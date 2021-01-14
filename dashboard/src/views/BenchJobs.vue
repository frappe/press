<template>
	<Section
		title="Jobs"
		:description="
			jobs.length
				? 'History of jobs that ran on your bench'
				: 'No jobs ran on your bench'
		"
	>
		<div class="flex" v-if="jobs.length">
			<div
				class="w-full py-4 overflow-auto text-base border rounded-md sm:w-1/3 sm:rounded-r-none"
				:class="{ 'hidden sm:block': selectedJob }"
			>
				<router-link
					class="block px-6 py-3 cursor-pointer"
					:class="
						selectedJob && selectedJob.name === job.name
							? 'bg-gray-100'
							: 'hover:bg-gray-50'
					"
					v-for="job in jobs"
					:key="job.name"
					:to="`/benches/${bench.name}/jobs/${job.name}`"
				>
					<div class="flex items-center justify-between">
						<span>
							{{ job.job_type }}
						</span>
						<Badge
							v-if="
								runningJob &&
									runningJob.id == job.name &&
									runningJob.status !== 'Success'
							"
							:status="runningJob.status"
						>
							{{ runningJob.status }}
						</Badge>
					</div>
					<div class="text-sm text-gray-600">
						<FormatDate>
							{{ job.creation }}
						</FormatDate>
					</div>
				</router-link>
			</div>
			<div class="w-full sm:w-2/3" v-if="selectedJob">
				<router-link
					:to="`/benches/${bench.name}/jobs`"
					class="flex items-center py-4 -mt-4 sm:hidden"
				>
					<FeatherIcon name="arrow-left" class="w-4 h-4" />
					<span class="ml-2">
						Select another Job
					</span>
				</router-link>
				<div class="min-h-full pb-16 -mx-4 bg-black sm:mx-0">
					<div class="px-6 py-4 mb-2 border-b border-gray-900">
						<div class="text-sm font-semibold text-white">
							{{ selectedJob.job_type }}
						</div>
						<div
							class="text-xs text-gray-500"
							v-if="selectedJob.status === 'Success'"
						>
							Completed
							<FormatDate type="relative">
								{{ selectedJob.creation }}
							</FormatDate>
							in {{ formatDuration(selectedJob.duration) }}
						</div>
					</div>
					<details
						class="px-6 text-white cursor-pointer"
						v-for="step in selectedJob.steps"
						:key="step.step_name"
					>
						<summary
							class="inline-flex items-center py-2 text-xs text-gray-600 focus:outline-none"
						>
							<span class="ml-1">
								<Spinner
									v-if="step.status === 'Running'"
									class="w-3 h-3 text-gray-500"
								/>
								<FeatherIcon
									v-else-if="step.status === 'Success'"
									name="check"
									:stroke-width="3"
									class="w-3 h-3 text-green-500"
								/>
								<FeatherIcon
									v-else-if="step.status === 'Failure'"
									name="x"
									:stroke-width="3"
									class="w-3 h-3 text-red-500"
								/>
								<FeatherIcon
									v-else-if="step.status === 'Skipped'"
									name="minus"
									:stroke-width="3"
									class="w-3 h-3 text-gray-500"
								/>
							</span>
							<span class="ml-2 font-semibold text-white">
								{{ step.step_name }}
							</span>
						</summary>
						<div class="px-6 font-mono text-xs text-gray-200">
							<div class="overflow-auto">
								<pre>{{ step.output }}</pre>
							</div>
						</div>
					</details>
				</div>
			</div>
		</div>
	</Section>
</template>

<script>
export default {
	name: 'BenchJobs',
	props: ['bench', 'jobName'],
	data: () => ({
		runningJob: null
	}),
	watch: {
		jobName(value) {
			if (value) {
				this.$resources.selectedJob.reload();
			}
		}
	},
	mounted() {
		if (this.jobName) {
			this.$resources.selectedJob.reload();
			this.setupSocket();
		}
		this.setupSocket();
	},
	methods: {
		setupSocket() {
			if (this._socketSetup) return;
			this._socketSetup = true;

			this.$socket.on('agent_job_update', data => {
				this.runningJob = data;
				if (this.runningJob.current.status === 'Success') {
					this.$resources.jobs.reload();
				}
				if (this.runningJob.id === this.selectedJob.id) {
					this.$resources.selectedJob.reload();
				}
			});
		},
		formatDuration(duration) {
			return duration.split('.')[0];
		}
	},
	resources: {
		jobs() {
			return {
				method: 'press.api.bench.jobs',
				params: {
					name: this.bench.name
				},
				auto: true,
				default: [],
				onSuccess(jobs) {
					if (jobs && !this.jobName) {
						this.$router.push(
							`/benches/${this.bench.name}/jobs/${jobs[0].name}`
						);
					}
				}
			};
		},
		selectedJob() {
			return {
				method: 'press.api.bench.job',
				params: {
					name: this.bench.name,
					job: this.jobName
				},
				auto: false
			};
		}
	},
	computed: {
		selectedJob() {
			return this.$resources.selectedJob.data;
		},
		jobs() {
			return this.$resources.jobs.data;
		}
	}
};
</script>
