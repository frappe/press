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
					<h1 class="text-2xl font-medium">{{ site.name }}</h1>
					<Badge class="ml-4" :status="site.status">{{ site.status }}</Badge>
				</div>
				<a
					v-if="site.status === 'Active' || site.status === 'Updating'"
					:href="`https://${site.name}`"
					target="_blank"
					class="inline-flex items-baseline text-sm text-blue-500 hover:underline"
				>
					Visit Site
					<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
				</a>
			</div>
			<div
				class="inline-block mb-4"
				v-if="site.status == 'Active' && !site.setup_wizard_complete"
			>
				<div
					class="items-center px-4 py-3 text-sm text-orange-700 bg-orange-100 border border-orange-300 rounded-md sm:flex"
				>
					<FeatherIcon name="alert-circle" class="w-4 h-4 mr-2" />
					<span>
						Please
						<a
							@click="loginAsAdministrator(siteName)"
							class="border-b border-orange-700 cursor-pointer"
						>
							login
						</a>
						and complete the setup wizard on your site. Analytics will be
						collected only after setup is complete.
					</span>
				</div>
			</div>
		</div>
		<div class="px-4 sm:px-8" v-if="site">
			<div>
				<ul class="hidden overflow-hidden text-sm border-b sm:flex">
					<router-link
						v-for="tab in tabs"
						:key="tab.label"
						:to="`/sites/${siteName}/${tab.route}`"
						v-slot="{ href, route, navigate, isActive, isExactActive }"
					>
						<li>
							<a
								class="block px-1 py-4 mr-8 font-medium leading-none border-b-2 border-transparent focus:outline-none"
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
					class="block w-full sm:hidden form-select"
					@change="e => changeTab(`/sites/${siteName}/${e.target.value}`)"
				>
					<option
						v-for="tab in tabs"
						:selected="isTabSelected(tab)"
						:value="tab.route"
						:key="tab.label"
					>
						{{ tab.label }}
					</option>
				</select>
			</div>
			<div class="w-full pt-6 pb-32 sm:pt-10">
				<router-view v-bind="{ site }"></router-view>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Site',
	props: ['siteName'],
	resources: {
		site() {
			return {
				method: 'press.api.site.get',
				params: {
					name: this.siteName
				},
				auto: true,
				onSuccess: async () => {
					if (
						this.site.status === 'Active' &&
						!this.site.setup_wizard_complete
					) {
						this.site.setup_wizard_complete = Boolean(
							await this.$call('press.api.site.setup_wizard_complete', {
								name: this.siteName
							})
						);
					}
				}
			};
		}
	},
	provide() {
		return {
			utils: {
				loginAsAdministrator: this.loginAsAdministrator
			}
		};
	},
	activated() {
		this.setupSocket();
		this.$resources.site.once('onSuccess', () => {
			if (this.$route.matched.length === 1) {
				let path = this.$route.fullPath;
				let tab = 'general';
				if (['Pending', 'Installing'].includes(this.site.status)) {
					tab = 'installing';
				}
				this.$router.replace(`${path}/${tab}`);
			}
		});
	},
	methods: {
		isTabSelected(tab) {
			return this.$route.path.endsWith(tab.route);
		},
		changeTab(route) {
			this.$router.push(route);
		},
		async loginAsAdministrator(siteName) {
			let sid = await this.$call('press.api.site.login', {
				name: siteName
			});
			if (sid) {
				window.open(`https://${siteName}/desk?sid=${sid}`, '_blank');
			}
		},
		setupSocket() {
			if (this._socketSetup) return;
			this._socketSetup = true;
			this.$store.socket.on('agent_job_update', data => {
				if (data.name === 'New Site' || data.name === 'New Site from Backup') {
					if (data.status === 'Success' && data.site === this.siteName) {
						this.$resources.site.reload();
					}
				}
			});
			this.$store.socket.on('list_update', ({ doctype, name }) => {
				if (doctype === 'Site' && name === this.siteName) {
					this.$resources.site.reload();
				}
			});
		}
	},
	computed: {
		site() {
			return this.$resources.site.data;
		},
		tabs() {
			let tabs = [
				{ label: 'General', route: 'general' },
				{ label: 'Installing', route: 'installing' },
				{ label: 'Plan', route: 'plan' },
				{ label: 'Apps', route: 'apps' },
				{ label: 'Domains', route: 'domains' },
				{ label: 'Analytics', route: 'analytics' },
				{ label: 'Backups', route: 'backups' },
				{ label: 'Site Config', route: 'site-config' },
				{ label: 'Activity', route: 'activity' },
				{ label: 'Jobs', route: 'jobs' }
			];

			let tabsByStatus = {
				Active: [
					'General',
					'Plan',
					'Apps',
					'Domains',
					'Analytics',
					'Backups',
					'Site Config',
					'Activity',
					'Jobs'
				],
				Inactive: ['General', 'Plan', 'Site Config', 'Jobs'],
				Installing: ['Installing', 'Jobs'],
				Pending: ['Installing', 'Jobs'],
				Broken: ['General', 'Plan', 'Jobs']
			};
			if (this.site) {
				let tabsToShow = tabsByStatus[this.site.status];
				if (tabsToShow?.length) {
					return tabs.filter(tab => tabsToShow.includes(tab.label));
				}
				return tabs;
			}
			return [];
		}
	}
};
</script>
