<template>
	<CardWithDetails
		title="Jobs"
		subtitle="History of jobs that ran on your site"
		:showDetails="jobName"
	>
		<div>
			<router-link
				class="block px-2.5 rounded-md cursor-pointer"
				:class="jobName === job.name ? 'bg-gray-100' : 'hover:bg-gray-50'"
				v-for="job in $resources.jobs.data"
				:key="job.name"
				:to="`/sites/${site.name}/jobs/${job.name}`"
			>
				<ListItem :title="job.job_type" :description="formatDate(job.creation)">
					<template slot="actions">
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
						<Badge v-else-if="job.status != 'Success'" :status="job.status">
							{{ job.status }}
						</Badge>
					</template>
				</ListItem>
				<div class="border-b"></div>
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
		<template #details>
			<SiteJobsDetail :jobName="jobName" />
		</template>
	</CardWithDetails>
</template>
<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import SiteJobsDetail from './SiteJobsDetail.vue';
export default {
	name: 'SiteJobs',
	props: ['site', 'jobName'],
	components: { SiteJobsDetail, CardWithDetails },
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
		this.$socket.on('agent_job_update', this.onAgentJobUpdate);
	},
	destroyed() {
		this.$socket.off('agent_job_update', this.onAgentJobUpdate);
	},
	methods: {
		onAgentJobUpdate(data) {
			if (data.site === this.site.name) {
				this.runningJob = data;
				if (this.runningJob.status === 'Success') {
					setTimeout(() => {
						// calling reload immediately does not fetch the latest status
						// so adding 1 sec delay
						this.$resources.jobs.reset();
						this.$resources.jobs.reload();
					}, 1000);
				}
			}
		}
	}
};
</script>
