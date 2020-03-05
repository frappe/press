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
					v-if="site.status === 'Active'"
					:href="`https://${site.name}`"
					target="_blank"
					class="inline-flex items-baseline hover:underline text-blue-500 text-sm"
				>
					Visit Site
					<FeatherIcon name="external-link" class="ml-1 w-3 h-3" />
				</a>
			</div>
			<div class="w-full sm:w-1/2 mb-4" v-if="setupComplete === false">
				<div
					class="sm:flex justify-between items-center bg-orange-100 border border-orange-300 rounded-md px-4 py-4 text-orange-700 text-sm"
				>
					<span>
						Please complete the setup wizard on your site. Analytics will be
						collected only after setup is complete.
					</span>
					<Button
						class="mt-4 sm:mt-0 sm:ml-4 flex items-center hover:bg-orange-200 border border-orange-200"
						@click="$store.sites.loginAsAdministrator(siteName)"
					>
						Login
						<FeatherIcon name="arrow-right" class="ml-2 w-4 h-4" />
					</Button>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="site">
			<div>
				<ul class="hidden sm:flex rounded overflow-hidden text-sm border-b">
					<router-link
						v-for="tab in tabs"
						:key="tab.label"
						:to="`/sites/${siteName}/${tab.route}`"
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
					@change="e => changeTab(`/sites/${siteName}/${e.target.value}`)"
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
	</div>
</template>

<script>
export default {
	name: 'Site',
	props: ['siteName'],
	data: () => ({
		site: null,
		setupComplete: null
	}),
	async mounted() {
		await this.fetchSite();
		if (this.site.status === 'Active') {
			this.setupComplete = Boolean(
				await this.$call('press.api.site.setup_wizard_complete', {
					name: this.siteName
				})
			);
		}

		this.$store.socket.on('agent_job_update', data => {
			if (data.site === this.site.name && data.name === 'New Site') {
				if (data.status === 'Success') {
					this.fetchSite();
				}
			}
		});

		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/general`);
		}
	},
	methods: {
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
	},
	computed: {
		tabs() {
			let tabs = [
				{ label: 'General', route: 'general' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Backups', route: 'backups' },
				{ label: 'Site Config', route: 'site-config' },
				{ label: 'Console', route: 'console' },
				{ label: 'Drop Site', route: 'drop-site' },
				{ label: 'Access Control', route: 'access-control' },
				{ label: 'Jobs', route: 'jobs' }
			];
			let tabsToShowForInactiveSite = ['General', 'Jobs'];
			if (this.site) {
				if (this.site.status !== 'Active') {
					return tabs.filter(tab =>
						tabsToShowForInactiveSite.includes(tab.label)
					);
				}
				return tabs;
			}
			return [];
		}
	}
};
</script>
