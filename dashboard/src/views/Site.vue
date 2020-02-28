<template>
	<div>
		<PageHeader v-if="siteName">
			<template slot="title">
				<div class="flex items-center">
					<router-link to="/sites" class="flex items-center">
						<FeatherIcon name="arrow-left" class="w-4 h-4" />
						<span class="ml-2 text-base">Back</span>
					</router-link>
				</div>
			</template>
		</PageHeader>
		<div class="px-4 sm:px-8" v-if="site">
			<div class="border-t"></div>
			<div class="py-8">
				<div class="flex items-center">
					<h1 class="font-medium text-2xl">{{ site.name }}</h1>
					<Badge class="ml-4" :status="site.status">{{ site.status }}</Badge>
				</div>
				<a
					:href="`https://${site.name}`"
					target="_blank"
					class="inline-flex items-baseline hover:underline text-blue-500 text-sm"
				>
					Visit Site
					<FeatherIcon name="external-link" class="ml-1 w-3 h-3" />
				</a>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="site && site.status === 'Active'">
			<div>
				<ul class="hidden sm:flex rounded overflow-hidden text-sm border-b">
					<router-link
						v-for="tab in tabs"
						:key="tab.label"
						:to="tab.route"
						v-slot="{ href, route, navigate, isActive, isExactActive }"
					>
						<li>
							<a
								class="mr-8 px-1 py-4 border-b-2 border-transparent font-medium leading-none block focus:outline-none"
								:class="[
									isExactActive
										? 'border-brand text-brand'
										: 'text-gray-800 hover:text-gray-900'
								]"
								:href="href"
								@click="navigate"
							>
								{{ tab.label }}
							</a>
						</li>
					</router-link>
				</ul>
				<select
					class="block sm:hidden form-select w-full"
					@change="e => changeTab(e.target.value)"
				>
					<option
						v-for="tab in tabs"
						:selected="isTabSelected(tab)"
						:value="tab.route"
					>
						{{ tab.label }}
					</option>
				</select>
			</div>
			<div class="w-full pt-6 sm:pt-10 pb-32">
				<router-view v-bind="{ site }"></router-view>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="installingJob">
			<section>
				<h2 class="font-medium text-lg">Your site is being installed..</h2>
				<p class="text-gray-600">
					Please wait while we set up your site for use.
				</p>
				<div
					class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4"
				>
					<div
						v-for="step in installingJob.steps"
						class="flex items-center py-2"
					>
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
	</div>
</template>

<script>
export default {
	name: 'Site',
	props: ['siteName'],
	data: () => ({
		site: null,
		tabs: [
			{ label: 'General', route: 'general' },
			{ label: 'Analytics', route: 'analytics' },
			{ label: 'Backups', route: 'backups' },
			{ label: 'Site Config', route: 'site-config' },
			{ label: 'Console', route: 'console' },
			{ label: 'Drop Site', route: 'drop-site' },
			{ label: 'Access Control', route: 'access-control' },
			{ label: 'Jobs', route: 'jobs' }
		],
		iconMap: {
			Running: 'loader',
			Success: 'check',
			Pending: 'minus'
		},
		installingJob: null
	}),
	async mounted() {
		await this.fetchSite();
		this.setupSiteInstall();

		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/general`);
		}
	},
	methods: {
		setupSiteInstall() {
			if (['Pending', 'Installing'].includes(this.site.status)) {
				this.$store.socket.on('agent_job_update', data => {
					if (data.site === this.site.name && data.name === 'New Site') {
						this.installingJob = data;

						if (data.status === 'Success') {
							this.installingJob = null;
							this.fetchSite();
						}
					}
				});
			}
		},
		async fetchSite() {
			this.site = await this.$call('press.api.site.get', {
				name: this.siteName
			});
		},
		isTabSelected(tab) {
			return this.$route.path.endsWith(tab.route);
		},
		changeTab(route) {
			this.$router.push(route);
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
