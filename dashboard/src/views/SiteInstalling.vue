<template>
	<Section
		v-if="installingJob"
		title="Your site is being installed..."
		description="Please wait while we set up your site for use"
	>
		<SectionCard>
			<div
				v-for="step in installingJob.steps"
				class="flex items-center px-6 py-2 text-base"
				:key="step.name"
			>
				<div class="h-4 w-4 text-gray-800">
					<FeatherIcon
						class="h-4 w-4"
						:class="{ spin: step.status === 'Running' }"
						:name="iconMap[step.status]"
					/>
				</div>
				<span class="ml-2">{{ step.name }}</span>
			</div>
		</SectionCard>
	</Section>
</template>

<script>
export default {
	name: 'SiteActivity',
	props: ['site'],
	data() {
		return {
			iconMap: {
				Running: 'loader',
				Success: 'check',
				Pending: 'minus'
			},
			installingJob: null
		};
	},
	mounted() {
		this.setupSiteInstall();
		this.fetchPendingJobs();
	},
	methods: {
		setupSiteInstall() {
			this.$socket.on('agent_job_update', (data) => {
				if (
					data.site === this.site.name &&
					(data.name === 'New Site' || data.name === 'New Site from Backup')
				) {
					this.installingJob = data;

					if (
						data.status === 'Success' &&
						this.$route.path.startsWith(`/sites/${this.site.name}`)
					) {
						this.installingJob = null;
						this.$router.replace(`/sites/${this.site.name}`);
						window.location.reload();
					}
				}
			});
		},
		async fetchPendingJobs() {
			let jobs = await this.$call('press.api.site.running_jobs', {
				name: this.site.name
			});
			jobs.forEach((job) => {
				if (job.name === 'New Site' || job.name === 'New Site from Backup') {
					this.installingJob = job;
				}
			});
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
