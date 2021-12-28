<template>
	<CardWithDetails
		title="Versions"
		subtitle="Deployed versions of your bench"
		:showDetails="selectedVersion"
	>
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
			<div
				class="w-full px-6 py-5 space-y-4 border-l md:w-2/3"
				v-if="selectedVersion"
			>
				<section>
					<div class="flex items-center justify-between">
						<Button
							class="mr-3 md:hidden"
							@click="$router.back()"
							icon="chevron-left"
						/>
						<div>
							<h4 class="text-lg font-medium">{{ selectedVersion.name }}</h4>
							<p class="mt-1 text-sm text-gray-600">
								{{
									selectedVersion.deployed_on
										? `Deployed on ${formatDate(
												selectedVersion.deployed_on,
												'DATETIME_SHORT'
										  )}`
										: ''
								}}
							</p>
						</div>
						<router-link
							class="text-base text-blue-500 hover:text-blue-600"
							:to="`/benches/${bench.name}/logs/${selectedVersion.name}/`"
						>
							View Logs →
						</router-link>
					</div>
					<h5 class="mt-4 text-lg font-semibold">Sites</h5>
					<div class="mt-2">
						<SiteList
							class="sm:border-gray-200 sm:shadow-none"
							:sites="selectedVersion.sites || []"
						/>
					</div>
				</section>
				<section>
					<h5 class="text-lg font-semibold">Apps</h5>
					<div class="py-2 mt-2 divide-y rounded-lg sm:border sm:px-4">
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
	inject: ['viewportWidth'],
	resources: {
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: { name: this.bench.name },
				auto: true,
				onSuccess() {
					if (
						!this.version &&
						this.versions.data.length > 0 &&
						this.viewportWidth > 768
					) {
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
