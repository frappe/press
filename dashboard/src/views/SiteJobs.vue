<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Jobs</h2>
			<p class="text-gray-600">History of jobs that ran on your site</p>
			<div class="mt-6 flex">
				<div class="w-1/3 py-4 rounded-l-md border overflow-auto">
					<div
						class="px-6 py-3 cursor-pointer"
						:class="
							selectedJob && selectedJob.name === job.name
								? 'bg-gray-100'
								: 'hover:bg-gray-50'
						"
						v-for="job in jobs"
						:key="job.name"
						@click="selectJob(job)"
					>
						<div>
							{{ job.job_type }}
						</div>
						<div class="text-gray-600 text-sm">
							<FormatDate>
								{{ job.creation }}
							</FormatDate>
						</div>
					</div>
				</div>
				<div v-if="selectedJob" class="w-2/3 bg-black pb-16">
					<div class="mb-2 py-4 px-6 border-b border-gray-900">
						<div class="text-white text-sm font-semibold">
							{{ selectedJob.job_type }}
						</div>
						<div
							class="text-xs text-gray-800"
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
					>
						<summary
							class="py-2 inline-flex items-center text-gray-600 text-xs focus:outline-none"
						>
							<span class="ml-1">
								<FeatherIcon
									v-if="step.status === 'Success'"
									name="check"
									:stroke-width="3"
									class="w-3 h-3 text-green-500"
								/>
								<FeatherIcon
									v-if="step.status === 'Failure'"
									name="x"
									:stroke-width="3"
									class="w-3 h-3 text-red-500"
								/>
								<FeatherIcon
									v-if="step.status === 'Skipped'"
									name="minus"
									:stroke-width="3"
									class="w-3 h-3 text-gray-500"
								/>
							</span>
							<span class="ml-2 text-white font-semibold">
								{{ step.step_name }}
							</span>
						</summary>
						<div class="text-gray-200 font-mono text-xs">
							<div>
								{{ step.output }}
							</div>
							<div>
								{{ step.traceback }}
							</div>
						</div>
					</details>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteJobs',
	props: ['site'],
	data: () => ({
		jobs: [],
		selectedJob: null
	}),
	mounted() {
		this.fetchJobs();
	},
	methods: {
		async fetchJobs() {
			this.jobs = await this.$call('press.api.site.jobs', {
				name: this.site.name
			});
		},
		async selectJob(job) {
			this.selectedJob = await this.fetchJobDetails(job.name);
		},
		async fetchJobDetails(name) {
			return await this.$call('press.api.site.job', {
				name
			});
		},
		formatDuration(duration) {
			return duration.split('.')[0];
		}
	}
};
</script>
