<template>
	<CardWithDetails :title="title" :subtitle="subtitle" :showDetails="jobName">
		<div>
			<router-link
				v-for="job in $resources.jobs.data"
				class="block cursor-pointer rounded-md px-2.5"
				:class="jobName === job.name ? 'bg-gray-100' : 'hover:bg-gray-50'"
				:key="job.name"
				:to="jobRoute(job)"
			>
				<ListItem :title="job.job_type" :description="formatDate(job.creation)">
					<template v-slot:actions>
						<Badge
							v-if="
								runningJob &&
								runningJob.id == job.name &&
								runningJob.status !== 'Success'
							"
							:label="runningJob.status"
						/>
						<Badge v-else-if="job.status != 'Success'" :label="job.status" />
					</template>
				</ListItem>
				<div class="border-b"></div>
			</router-link>
			<div class="py-3" v-if="$resources.jobs.hasNextPage">
				<Button
					:loading="$resources.jobs.list.loading"
					loadingText="Loading..."
					@click="$resources.jobs.next()"
				>
					Load more
				</Button>
			</div>
		</div>
		<template #details>
			<JobsDetail :jobName="jobName" />
		</template>
	</CardWithDetails>
</template>
<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import JobsDetail from './JobsDetail.vue';
export default {
	name: 'AgentJobs',
	props: ['title', 'subtitle', 'resource', 'jobName', 'jobRoute'],
	components: { JobsDetail, CardWithDetails },
	data() {
		return {
			runningJob: null
		};
	},
	resources: {
		jobs() {
			return this.resource();
		}
	},
	mounted() {
		this.$socket.on('agent_job_update', this.onAgentJobUpdate);
	},
	unmounted() {
		this.$socket.off('agent_job_update', this.onAgentJobUpdate);
	},
	methods: {
		onAgentJobUpdate(data) {
			if (data.id === this.jobName) {
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
