<template>
	<Section title="Jobs" description="History of jobs that ran on your site">
		<div class="flex">
			<div
				class="w-full py-4 overflow-auto border rounded-md sm:w-1/3 sm:rounded-r-none"
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
					:to="`/sites/${site.name}/jobs/${job.name}`"
				>
					<div>
						{{ job.job_type }}
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
					:to="`/sites/${site.name}/jobs`"
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
						:key="step.step_name"
					>
						<summary
							class="inline-flex items-center py-2 text-xs text-gray-600 focus:outline-none"
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
	name: 'SiteJobs',
	props: ['site', 'jobName'],
	data: () => ({
		jobs: [],
		selectedJob: null
	}),
	watch: {
		jobName(value) {
			if (!value) {
				this.selectedJob = null;
			} else {
				this.fetchJobDetails();
			}
		}
	},
	mounted() {
		this.fetchJobs();
		this.fetchJobDetails();
	},
	methods: {
		async fetchJobs() {
			this.jobs = await this.$call('press.api.site.jobs', {
				name: this.site.name
			});
			if (this.jobs && !this.jobName) {
				this.$router.push(`/sites/${this.site.name}/jobs/${this.jobs[0].name}`);
			}
		},
		async selectJob(jobName) {
			this.selectedJob = await this.fetchJobDetails(jobName);
		},
		async fetchJobDetails() {
			if (this.jobName) {
				this.selectedJob = await this.$call('press.api.site.job', {
					name: this.site.name,
					job: this.jobName
				});
			}
		},
		formatDuration(duration) {
			return duration.split('.')[0];
		}
	}
};
</script>
