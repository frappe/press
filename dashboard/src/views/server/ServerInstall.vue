<template>
	<Section
		v-if="creationJob"
		title="Your server is being setup ..."
		description="Please wait while we set up your server for use"
	>
		<SectionCard>
			<div
				v-for="step in creationJob.steps"
				class="flex items-center px-6 py-2 text-base"
				:key="step.name"
			>
				<div class="h-4 w-4 text-gray-800">
					<Spinner
						class="h-3 w-3 text-gray-500"
						v-if="step.status === 'Running'"
					/>
					<FeatherIcon
						v-else
						class="h-4 w-4"
						:class="{ spin: step.status === 'Running' }"
						:name="iconMap[step.status]"
					/>
				</div>
				<span class="ml-2">{{ step.step_name }}</span>
			</div>
		</SectionCard>
	</Section>
</template>

<script>
export default {
	name: 'ServerInstall',
	props: ['server'],
	data() {
		return {
			iconMap: {
				Running: 'loader',
				Success: 'check',
				Pending: 'minus'
			},
			creationJob: null
		};
	},
	mounted() {
		this.$socket.on('press_job_update', this.onPressJobUpdate);
		this.fetchJob();
	},
	unmounted() {
		this.$socket.emit('doc_unsubscribe', 'Press Job', this.creationJob.name);
		this.$socket.off('press_job_update', this.onPressJobUpdate);
	},
	methods: {
		onPressJobUpdate(data) {
			if (
				data.server === this.server.name &&
				data.job_type === 'Create Server'
			) {
				this.creationJob = data;
				if (
					data.status === 'Success' &&
					this.$route.path.startsWith(`/servers/${this.server.name}`)
				) {
					this.creationJob = null;
					this.$router.replace(`/servers/${this.server.name}/overview`);
				}
			}
		},
		async fetchJob() {
			let jobs = await this.$call('press.api.server.press_jobs', {
				name: this.server.name
			});
			jobs.forEach(job => {
				if (job.job_type === 'Create Server') {
					this.creationJob = job;
					this.$socket.emit('doc_subscribe', 'Press Job', job.name);
				}
			});
			if (this.creationJob?.status === 'Success') {
				this.$router.replace(`/servers/${this.server.name}/overview`);
			}
		}
	}
};
</script>

<style>
.spin {
	animation: spin 4s linear infinite;
}

@keyframes spin {
	100% {
		transform: rotate(360deg);
	}
}
</style>
