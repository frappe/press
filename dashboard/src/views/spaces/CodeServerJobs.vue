<template>
	<AgentJobs
		title="Jobs"
		subtitle="History of jobs that ran on your site"
		:resource="jobResource"
		:jobName="jobName"
		:jobRoute="jobRoute"
	/>
</template>
<script>
import AgentJobs from '@/views/general/AgentJobs.vue';
export default {
	name: 'SiteJobs',
	props: ['codeServer', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource(start) {
			return {
				method: 'press.api.spaces.code_server_jobs',
				params: { name: this.codeServer?.name, start },
				pageLength: 10,
				keepData: true,
				auto: true
			};
		},
		jobRoute(job) {
			return `/codeservers/${this.codeServer.name}/jobs/${job.name}`;
		}
	}
};
</script>
