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
	props: ['bench', 'jobName'],
	components: {
		AgentJobs
	},
	methods: {
		jobResource(start) {
			return {
				method: 'press.api.bench.jobs',
				params: { name: this.bench?.name, start },
				auto: true,
				pageLength: 10,
				keepData: true
			};
		},
		jobRoute(job) {
			return `/benches/${this.bench?.name}/jobs/${job.name}`;
		}
	}
};
</script>
