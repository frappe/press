<template>
	<CardWithDetails title="Versions" subtitle="Deployed versions of your bench">
		<div>
			<router-link
				v-for="v in $resources.versions.data"
				class="block px-2.5 rounded-md cursor-pointer"
				:class="
					selectedVersion && v.name === selectedVersion.name
						? 'bg-gray-100'
						: 'hover:bg-gray-50'
				"
				:key="v.name"
				:to="getRoute(v)"
			>
				<ListItem
					:title="v.name"
					:subtitle="
						v.deployed_on
							? `Deployed on ${formatDate(v.deployed_on, 'DATETIME_SHORT')}`
							: ''
					"
				>
					<template #actions>
						<Badge v-if="v.status != 'Active'" :status="v.status" />
						<Badge v-else color="green">
							{{ v.sites.length }}
							{{ $plural(v.sites.length, 'site', 'sites') }}
						</Badge>
					</template>
				</ListItem>
				<div class="border-b"></div>
			</router-link>
			<Button
				:loading="true"
				loadingText="Loading..."
				v-if="$resources.versions.loading"
			/>
		</div>
		<template #details>
			<div class="w-2/3 px-6 py-5 space-y-4 border-l" v-if="selectedVersion">
				<section>
					<h4 class="text-lg font-semibold">Sites</h4>
					<div class="mt-2">
						<SiteList
							class="sm:border-gray-200 sm:shadow-none"
							:sites="selectedVersion.sites || []"
						/>
					</div>
				</section>
				<section>
					<h4 class="text-lg font-semibold">Apps</h4>
					<div class="px-4 py-2 mt-2 border divide-y rounded-lg">
						<ListItem
							v-for="app in selectedVersion.apps"
							:key="app.app"
							:title="app.app"
							:subtitle="
								`${app.repository_owner}/${app.repository}:${app.branch}`
							"
						>
							<template #actions>
								<a
									class="block ml-2 cursor-pointer"
									:href="`${app.repository_url}/commit/${app.hash}`"
									target="_blank"
								>
									<Badge
										class="cursor-pointer hover:text-blue-500"
										color="blue"
									>
										{{ app.tag || app.hash.substr(0, 7) }}
									</Badge>
								</a>
							</template>
						</ListItem>
					</div>
				</section>
			</div>
		</template>
	</CardWithDetails>
</template>
<script>
import CardWithDetails from '../components/CardWithDetails.vue';
import SiteList from './SiteList.vue';
export default {
	name: 'BenchApps',
	props: ['bench', 'version'],
	components: {
		SiteList,
		CardWithDetails
	},
	resources: {
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: { name: this.bench.name },
				auto: true,
				onSuccess() {
					if (!this.version && this.versions.data.length > 0) {
						this.$router.replace(this.getRoute(this.versions.data[0]));
					}
				}
			};
		}
	},
	methods: {
		getRoute(version) {
			return `/benches/${this.bench.name}/sites/${version.name}`;
		}
	},
	computed: {
		selectedVersion() {
			if (this.version && this.versions.data) {
				return this.versions.data.find(v => v.name === this.version);
			}
		}
	}
};
</script>
