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
	props: ['server', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource(start) {
			return {
				method: 'press.api.server.jobs',
				params: { name: this.server?.name, start },
				paged: true,
				keepData: true,
				auto: true
			};
		},
		jobRoute(job) {
			return `/servers/${this.server.name}/jobs/${job.name}`;
		}
	}
};
</script>
