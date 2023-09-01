<template>
	<AgentJobs
		title="Jobs"
		subtitle="History of jobs that ran on your server"
		:resource="jobResource"
		:jobName="jobName"
		:jobRoute="jobRoute"
	/>
</template>
<script>
import AgentJobs from '@/views/general/AgentJobs.vue';
export default {
	name: 'ServerJobs',
	props: ['serverName', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource() {
			return {
				type: 'list',
				doctype: 'Agent Job',
				filters: { server: this.serverName },
				fields: [
					'name',
					'job_type',
					'creation',
					'status',
					'start',
					'end',
					'duration'
				],
				orderBy: 'creation desc',
				start: 0,
				pageLength: 10,
				auto: true
			};
		},
		jobRoute(job) {
			return `/servers/${this.serverName}/jobs/${job.name}`;
		}
	}
};
</script>
