<template>
	<div class="pb-20 mt-8">
		<div class="px-4 sm:px-8">
			<h1 class="sr-only">Dashboard</h1>
			<div class="flex flex-col sm:space-x-4 sm:flex-row">
				<div class="sm:w-2/12" v-if="multipleBenches">
					<Input
						class="mb-4 sm:hidden"
						type="select"
						:value="bench || 'shared'"
						:options="
							benches.map(d => ({
								label: benchTitle(d),
								value: d.name
							}))
						"
						@change="value => changeBench(value)"
					/>

					<div class="hidden space-y-1 sm:block">
						<router-link
							v-for="currentBench in benches"
							:key="currentBench.name"
							class="block px-3 py-2 text-base rounded-md hover:bg-gray-100"
							:class="
								(!bench && currentBench.shared) || bench === currentBench.name
									? 'bg-gray-100'
									: ''
							"
							:to="
								currentBench.shared ? '/sites' : `/${currentBench.name}/sites`
							"
						>
							{{ benchTitle(currentBench) }}
						</router-link>
					</div>
				</div>
				<div class="flex-1" v-if="activeBench">
					<div class="flex items-center justify-between">
						<div>
							<h2 class="font-bold">
								{{ activeBench.shared ? 'Sites' : activeBench.title }}
							</h2>
							<p v-if="benches" class="text-base text-gray-700">
								{{ sitesSubtitle(activeBench) }}
							</p>
						</div>
						<div class="flex items-center space-x-2">
							<Button
								v-if="activeBench.owned_by_team"
								:route="`/benches/${activeBench.name}`"
								icon-left="tool"
							>
								Manage Bench
							</Button>
							<Button
								:route="
									`/sites/new${
										activeBench.owned_by_team
											? `?bench=${activeBench.name}&benchTitle=${activeBench.title}`
											: ''
									}`
								"
								type="primary"
								iconLeft="plus"
								v-if="showNewSiteButton(activeBench)"
							>
								New Site
							</Button>
						</div>
					</div>
					<SiteList
						class="mt-4"
						:sites="activeBench.sites"
						v-if="!$resources.benches.loading"
					/>
					<div class="px-4 py-3 mt-4 rounded-md bg-gray-50" v-else>
						<Loading />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import SiteList from './SiteList.vue';
export default {
	name: 'Sites',
	props: ['bench'],
	components: {
		SiteList
	},
	resources: {
		benches: {
			method: 'press.api.site.all',
			auto: true
		}
	},
	mounted() {
		this.$socket.on('agent_job_update', this.onAgentJobUpdate);
		this.$socket.on('list_update', this.onSiteUpdate);
	},
	destroyed() {
		this.$socket.off('agent_job_update', this.onAgentJobUpdate);
		this.$socket.off('list_update', this.onSiteUpdate);
	},
	methods: {
		onAgentJobUpdate(data) {
			if (!(data.name === 'New Site' || data.name === 'New Site from Backup'))
				return;
			if (data.status === 'Success') {
				this.reload();
				this.$notify({
					title: 'Site creation complete!',
					message: 'Login to your site and complete the setup wizard',
					icon: 'check',
					color: 'green'
				});
			}
		},
		onSiteUpdate({ doctype }) {
			if (doctype === 'Site') {
				this.reload();
			}
		},
		reload() {
			// refresh if not reloaded in the last 1 second
			if (new Date() - this.$resources.benches.lastLoaded > 1000) {
				this.$resources.benches.reload();
			}
		},
		benchTitle(bench) {
			if (bench.shared) {
				return 'Shared Bench';
			}
			return bench.title || bench.name;
		},
		sitesSubtitle(bench) {
			let parts = [
				`${bench.sites.length} ${this.$plural(
					bench.sites.length,
					'site',
					'sites'
				)}`
			];

			let activeSites = bench.sites.filter(site => site.status == 'Active');
			if (activeSites.length) {
				parts.push(`${activeSites.length} active`);
			}

			let brokenSites = bench.sites.filter(site => site.status == 'Broken');
			if (brokenSites.length) {
				parts.push(`${brokenSites.length} broken`);
			}

			return parts.join(' · ');
		},
		showNewSiteButton(bench) {
			if (bench.status != 'Active') return false;
			return bench.shared || bench.owned_by_team;
		},
		changeBench(benchName) {
			let bench = this.benches.find(_bench => _bench.name === benchName);
			if (bench) {
				this.$router.replace(bench.shared ? '/sites' : `/${bench.name}/sites`);
			}
		}
	},
	computed: {
		activeBench() {
			if (this.benches) {
				if (this.bench) {
					return this.benches.find(bench => bench.name === this.bench);
				}
				return this.benches[0];
			}
			return {
				shared: true,
				sites: []
			};
		},
		benches() {
			if (this.$resources.benches.data) {
				return this.$resources.benches.data;
			}
			return null;
		},
		sharedBench() {
			if (this.benches) {
				return this.benches[0];
			}
			return null;
		},
		multipleBenches() {
			if (this.$resources.benches.data) {
				return this.$resources.benches.data.length > 1;
			}
		}
	}
};
</script>
