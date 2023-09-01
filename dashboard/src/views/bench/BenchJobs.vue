<template>
	<AgentJobs
		title="Jobs"
		subtitle="History of jobs that ran on your bench"
		:resource="jobResource"
		:jobName="jobName"
		:jobRoute="jobRoute"
	/>
</template>

<script>
import AgentJobs from '@/views/general/AgentJobs.vue';

export default {
	name: 'BenchJobs',
	props: ['benchName', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource() {
			return {
				type: 'list',
				doctype: 'Agent Job',
				url: 'press.api.bench.jobs',
				filters: { name: this.benchName },
				auto: true,
				orderBy: 'creation desc',
				start: 0,
				pageLength: 10
			};
		},
		jobRoute(job) {
			return `/benches/${this.benchName}/jobs/${job.name}`;
		}
	}
};
</script>
