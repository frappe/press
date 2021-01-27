<template>
	<div class="flex flex-col border rounded-lg shadow md:flex-row">
		<Card
			title="Jobs"
			subtitle="History of jobs that ran on your site"
			class="w-full border-none rounded-none shadow-none md:w-1/3"
			:class="{ 'hidden md:flex': jobName }"
			:style="{ height: viewportWidth > 768 ? 'calc(100vh - 16rem)' : null }"
		>
			<div class="w-full text-base md:rounded-r-none">
				<router-link
					class="block px-2.5 pt-3 rounded-md cursor-pointer"
					:class="jobName === job.name ? 'bg-gray-100' : 'hover:bg-gray-50'"
					v-for="job in $resources.jobs.data"
					:key="job.name"
					:to="`/sites/${site.name}/jobs/${job.name}`"
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
					<div class="pb-3 border-b"></div>
				</router-link>
				<div class="py-3" v-if="!$resources.jobs.lastPageEmpty">
					<Button
						:loading="$resources.jobs.loading"
						loadingText="Loading..."
						@click="pageStart += 10"
					>
						Load more
					</Button>
				</div>
			</div>
		</Card>
		<SiteJobsDetail :jobName="jobName" />
	</div>
</template>

<script>
import SiteJobsDetail from './SiteJobsDetail.vue';
export default {
	name: 'SiteJobs',
	props: ['site', 'jobName'],
	components: { SiteJobsDetail },
	data() {
		return {
			pageStart: 0,
			runningJob: null
		};
	},
	inject: ['viewportWidth'],
	resources: {
		jobs() {
			return {
				method: 'press.api.site.jobs',
				params: { name: this.site.name, start: this.pageStart },
				auto: true,
				paged: true,
				keepData: true
			};
		}
	},
	mounted() {
		this.setupRealtime();
	},
	destroyed() {
		this.$socket.off('agent_job_update', this.onAgentJobUpdate);
		this.onAgentJobUpdate = null;
	},
	methods: {
		setupRealtime() {
			if (this._realtimeSetup) return;

			this._realtimeSetup = true;
			this.onAgentJobUpdate = data => {
				this.runningJob = data;
				if (this.runningJob.current.status === 'Success') {
					this.fetchJobDetails();
				}
			};
			this.$socket.on('agent_job_update', this.onAgentJobUpdate);
		}
	}
};
</script>
