<template>
	<Card
		title="Versions"
		subtitle="Deployed versions of your bench"
		:loading="versions.loading"
	>
		<div class="divide-y">
			<div
				class="flex py-3"
				v-for="version in versions.data"
				:key="version.name"
			>
				<div>
					<div class="text-base font-medium">
						{{ version.name }}
					</div>
					<div class="text-base text-gray-700">
						{{ formatDate(version.deployed_on, 'DATETIME_FULL') }}
					</div>
				</div>
				<div class="ml-8">
					<Badge v-if="version.status != 'Active'" :status="version.status" />
					<Badge v-else color="green">
						{{ version.sites_count }}
						{{ $plural(version.sites_count, 'site', 'sites') }}
					</Badge>
				</div>
				<Dropdown class="ml-auto" :items="dropdownItems(version)" right>
					<template v-slot="{ toggleDropdown }">
						<Button icon="more-horizontal" @click="toggleDropdown()" />
					</template>
				</Dropdown>
			</div>
		</div>
		<Dialog :title="sitesDialogTitle" v-model="showSites">
			<Loading v-if="sitesInVersion.loading" />
			<div class="divide-y" v-else @click="showSites = false">
				<router-link
					class="block py-3 text-base hover:bg-gray-50 focus:outline-none focus:shadow-outline"
					v-for="site in sitesInVersion.data"
					:key="site.name"
					:to="'/sites/' + site.name"
				>
					<div>{{ site.name }}</div>
				</router-link>
			</div>
		</Dialog>
		<Dialog
			title="App Versions"
			:show="showAppVersions"
			@change="value => (!value ? (selectedVersion = null) : null)"
		>
			<div class="divide-y" v-if="selectedVersion">
				<div
					class="flex py-3"
					v-for="app in selectedVersion.apps"
					:key="app.app"
				>
					<div class="w-1/3 text-base font-medium">
						{{ app.repository_owner }}/{{ app.app }}
					</div>
					<div class="w-1/3 text-base">
						{{ app.tag || app.hash.substr(0, 7) }}
					</div>
					<div class="w-1/3 text-base text-right">
						<Link :to="`${app.repository_url}/commit/${app.hash}`">
							Open Commit →
						</Link>
					</div>
				</div>
			</div>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'BenchOverviewVersions',
	props: ['bench'],
	data() {
		return {
			selectedVersion: null,
			showSites: false
		};
	},
	resources: {
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: { name: this.bench.name },
				auto: true
			};
		},
		sitesInVersion() {
			return {
				method: 'press.api.bench.sites'
			};
		}
	},
	methods: {
		dropdownItems(version) {
			return [
				{
					label: 'Show sites',
					action: () => {
						this.showSites = true;
						this.$resources.sitesInVersion.fetch({
							name: this.bench.name,
							version: version.name
						});
					}
				},
				{
					label: 'Show app versions',
					action: () => {
						this.selectedVersion = version;
					}
				}
			];
		},
		benchDescription(version) {
			return `${version.status} · ${version.sites_count} sites`;
		}
	},
	computed: {
		showAppVersions() {
			return Boolean(this.selectedVersion);
		},
		sitesDialogTitle() {
			if (this.sitesInVersion.loading) {
				return 'Sites';
			}
			if (this.sitesInVersion.data) {
				let sites = this.$plural(
					this.sitesInVersion.data.length,
					'site',
					'sites'
				);
				return `${this.sitesInVersion.data.length} ${sites} on this version`;
			}
		}
	}
};
</script>
