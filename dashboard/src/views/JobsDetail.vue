<template>
	<StepsDetail
		:showDetails="job"
		:loading="$resources.job.loading"
		:title="job ? job.job_type : ''"
		:subtitle="subtitle"
		:steps="steps"
	/>
</template>
<script>
import StepsDetail from './StepsDetail.vue';
export default {
	name: 'JobsDetail',
	props: ['jobName'],
	components: {
		StepsDetail
	},
	inject: ['viewportWidth'],
	resources: {
		job() {
			return {
				method: 'press.api.site.job',
				params: {
					job: this.jobName
				},
				auto: Boolean(this.jobName)
			};
		}
	},
	data() {
		return {
			runningJob: null
		};
	},
	computed: {
		job() {
			return this.$resources.job.data;
		},
		subtitle() {
			if (!this.job) return;
			if (this.job.status == 'Success') {
				let when = this.formatDate(this.job.creation, 'relative');
				return `Completed ${when} in ${this.formatDuration(this.job.duration)}`;
			}
			if (this.job.status == 'Undelivered') {
				return 'Job failed to start';
			}
		},
		steps() {
			if (!this.job) return;
			return this.job.steps.map((step, index) => {
				return {
					name: step.step_name,
					status: step.status,
					output: step.output,
					running: this.isStepRunning(step),
					completed: this.isStepCompleted(step, index)
				};
			});
		}
	},
	mounted() {
		this.$socket.on('agent_job_update', this.onAgentJobUpdate);
	},
	unmounted() {
		this.$socket.off('agent_job_update', this.onAgentJobUpdate);
		this.runningJob = null;
	},
	methods: {
		onAgentJobUpdate(data) {
			if (data.id === this.jobName) {
				this.runningJob = data;
			}
		},
		formatDuration(duration) {
			return duration.split('.')[0];
		},
		isStepRunning(step) {
			if (!this.runningJob) return false;
			let runningStep = this.runningJob.steps.find(
				s => s.name == step.step_name
			);
			return runningStep?.status === 'Running';
		},
		isStepCompleted(step, index) {
			if (this.runningJob) {
				return this.runningJob.current.index > index;
			}
			return step.status === 'Success';
		}
	}
};
</script>
