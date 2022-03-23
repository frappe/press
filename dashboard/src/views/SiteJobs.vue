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
import AgentJobs from './AgentJobs.vue';
export default {
	name: 'SiteJobs',
	props: ['site', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource(start) {
			return {
				method: 'press.api.site.jobs',
				params: { name: this.site?.name, start },
				paged: true,
				keepData: true,
				auto: true
			};
		},
		jobRoute(job) {
			return `/sites/${this.site.name}/jobs/${job.name}`;
		}
	}
};
</script>
