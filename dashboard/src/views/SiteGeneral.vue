<template>
	<div v-if="!installingJob">
		<section>
			<h2 class="font-medium text-lg">Site information</h2>
			<p class="text-gray-600">General information about your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-2"
			>
				<div class="grid grid-cols-3 py-3 px-6 text-sm">
					<div class="text-gray-700 font-medium">Site name:</div>
					<div class="col-span-2 font-medium">{{ site.name }}</div>
				</div>
				<div class="grid grid-cols-3 py-3 border-t px-6 text-sm">
					<div class="text-gray-700 font-medium">Created:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ site.creation }}</FormatDate>
					</div>
				</div>
				<div class="grid grid-cols-3 py-3 border-t px-6 text-sm">
					<div class="text-gray-700 font-medium">Last update:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ site.last_updated }}</FormatDate>
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Installed apps</h2>
			<p class="text-gray-600">Apps installed on your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-4"
			>
				<a
					class="px-6 py-3 block hover:bg-gray-50"
					v-for="app in site.installed_apps"
					:href="`${app.url}/tree/${app.branch}`"
					:key="app.url"
					target="_blank"
				>
					<p class="font-medium text-brand">{{ app.owner }}/{{ app.repo }}</p>
					<p class="text-sm text-gray-800">
						{{ app.branch }}
					</p>
				</a>
			</div>
		</section>
		<section class="mt-10" v-if="domains">
			<h2 class="font-medium text-lg">Domains</h2>
			<p class="text-gray-600">Domains pointing to your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-4"
			>
				<div class="px-6 py-3 hover:bg-gray-50" v-for="d in domains" :key="d.domain">
					<div>
						{{ d.domain }}
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Activity</h2>
			<p class="text-gray-600">Activities performed on your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-4"
			>
				<div class="px-6 py-3 hover:bg-gray-50" v-for="a in activities" :key="a.creation">
					<div>
						{{ a.text }} <span class="text-gray-800">by {{ a.owner }}</span>
					</div>
					<div class="text-sm text-gray-600">
						<FormatDate>
							{{ a.creation }}
						</FormatDate>
					</div>
				</div>
			</div>
		</section>
	</div>
	<div v-else>
		<section>
			<h2 class="font-medium text-lg">Your site is being installed..</h2>
			<p class="text-gray-600">
				Please wait while we set up your site for use.
			</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4"
			>
				<div v-for="step in installingJob.steps" class="flex items-center py-2" :key="step.name">
					<div class="w-4 h-4 text-gray-800">
						<FeatherIcon
							class="w-4 h-4"
							:class="{ spin: step.status === 'Running' }"
							:name="iconMap[step.status]"
						/>
					</div>
					<span class="ml-2">{{ step.name }}</span>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteGeneral',
	props: ['site'],
	data() {
		return {
			activities: [],
			domains: [],
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
		this.fetchActivities();
		this.fetchDomains();
		this.fetchPendingJobs();
	},
	methods: {
		setupSiteInstall() {
			if (['Pending', 'Installing'].includes(this.site.status)) {
				this.$store.socket.on('agent_job_update', data => {
					if (data.site === this.site.name && data.name === 'New Site') {
						this.installingJob = data;

						if (data.status === 'Success') {
							this.installingJob = null;
						}
					}
				});
			}
		},
		async fetchActivities() {
			let activities = await this.$call('press.api.site.activities', {
				name: this.site.name
			});

			this.activities = activities.map(d => {
				let text =
					{
						Create: 'Site created'
					}[d.action] || d.action;
				return {
					...d,
					text
				};
			});
		},
		async fetchDomains() {
			this.domains = await this.$call('press.api.site.domains', {
				name: this.site.name
			});
		},
		async fetchPendingJobs() {
			let jobs = await this.$call('press.api.site.running_jobs', {
				name: this.site.name
			});
			jobs.forEach(job => {
				if (job.name === 'New Site') {
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
