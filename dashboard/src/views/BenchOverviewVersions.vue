<template>
	<Card
		title="Versions"
		subtitle="Deployed versions of your bench"
		:loading="versions.loading"
		v-if="versions.data && versions.data.length"
	>
		<div class="divide-y">
			<ListItem
				v-for="version in versions.data"
				:key="version.name"
				:title="version.name"
				:subtitle="
					// prettier-ignore
					version.status == 'Broken'
						? 'Contact support to resolve this issue'
						: version.deployed_on
							? formatDate(version.deployed_on, 'DATETIME_FULL')
							: null
				"
			>
				<template #actions>
					<div class="flex items-center space-x-2">
						<Badge v-if="version.status != 'Active'" :status="version.status" />
						<Badge v-else color="green">
							{{ version.sites.length }}
							{{ $plural(version.sites.length, 'site', 'sites') }}
						</Badge>
						<Dropdown class="ml-auto" :items="dropdownItems(version)" right>
							<template v-slot="{ toggleDropdown }">
								<Button icon="more-horizontal" @click="toggleDropdown()" />
							</template>
						</Dropdown>
					</div>
				</template>
			</ListItem>
		</div>
		<Dialog :title="sitesDialogTitle" v-model="showSites">
			<div class="divide-y" @click="showSites = false">
				<router-link
					class="block py-3 text-base hover:bg-gray-50 focus:outline-none focus:shadow-outline"
					v-for="site in sitesInDialog"
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
					class="flex items-center py-3"
					v-for="app in selectedVersion.apps"
					:key="app.app"
				>
					<div class="text-base font-medium">
						{{ app.repository_owner }}/{{ app.app }}
					</div>
					<a
						class="block ml-2 cursor-pointer"
						:href="`${app.repository_url}/commit/${app.hash}`"
						target="_blank"
					>
						<Badge class="cursor-pointer hover:text-blue-500" color="blue">
							{{ app.tag || app.hash.substr(0, 7) }}
						</Badge>
					</a>
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
			showSites: false,
			sitesInDialog: []
		};
	},
	resources: {
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: { name: this.bench.name },
				auto: true
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
						this.sitesInDialog = version.sites;
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
			return `${version.status} · ${version.sites.length} sites`;
		}
	},
	computed: {
		showAppVersions() {
			return Boolean(this.selectedVersion);
		},
		sitesDialogTitle() {
			let sites = this.$plural(this.sitesInDialog.length, 'site', 'sites');
			return `${this.sitesInDialog.length} ${sites} on this version`;
		}
	}
};
</script>
