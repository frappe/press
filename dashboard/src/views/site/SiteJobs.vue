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
	props: ['siteName', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource() {
			return {
				type: 'list',
				doctype: 'Agent Job',
				filters: { site: this.siteName },
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
			return `/sites/${this.siteName}/jobs/${job.name}`;
		}
	}
};
</script>
