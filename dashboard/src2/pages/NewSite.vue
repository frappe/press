<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[
					{ label: 'Sites', route: '/sites' },
					{ label: 'New Site', route: '/sites/new' }
				]"
			/>
		</Header>
	</div>

	<div class="mx-auto max-w-4xl">
		<div v-if="options" class="space-y-12 pb-[50vh] pt-12">
			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Frappe Framework Version
					</h2>
				</div>
				<div class="mt-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<button
							v-for="version in options.versions"
							:key="version.name"
							:class="[
								selectedVersion === version
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  hover:bg-gray-50',
								'flex cursor-pointer items-center justify-between rounded border border-gray-400 p-3 text-sm focus:outline-none'
							]"
							@click="selectedVersion = version"
						>
							<span class="font-medium">{{ version.name }} </span>
							<span class="ml-1 text-gray-600">
								{{ version.status }}
							</span>
						</button>
					</div>
				</div>
			</div>
			<div class="flex flex-col" v-if="selectedVersionApps.length">
				<h2 class="text-sm font-medium leading-6 text-gray-900">Select Apps</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-2">
						<button
							v-for="app in selectedVersionApps"
							:key="app"
							@click="toggleApp(app)"
							:class="[
								apps.includes(app.app)
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  hover:bg-gray-50',
								'flex w-full items-start space-x-2 rounded border p-2 text-left text-base text-gray-900'
							]"
						>
							<img :src="app.image" class="h-10 w-10 shrink-0" />
							<div class="w-full">
								<div class="flex w-full items-center justify-between">
									<div class="flex items-center">
										<div class="text-base font-medium">
											{{ app.app_title }}
										</div>
										<Tooltip
											v-if="app.total_installs > 1"
											:text="`${app.total_installs} installs`"
										>
											<div class="ml-2 flex items-center text-sm text-gray-600">
												<i-lucide-download class="h-3 w-3" />
												<span class="ml-0.5 leading-3">
													{{ $format.numberK(app.total_installs || '') }}
												</span>
											</div>
										</Tooltip>
									</div>
									<a
										:href="`/${app.route}`"
										target="_blank"
										title="App details"
									>
										<FeatherIcon name="external-link" class="h-4 w-4" />
									</a>
								</div>
								<div
									class="mt-1 line-clamp-1 overflow-clip text-p-sm text-gray-600"
									:title="app.description"
								>
									{{ app.description }}
								</div>
							</div>
						</button>
					</div>
				</div>
			</div>
			<div
				class="flex flex-col"
				v-if="selectedVersion?.group?.clusters?.length"
			>
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Select Region
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<button
							v-for="c in selectedVersion.group.clusters"
							:key="c.name"
							@click="cluster = c.name"
							:class="[
								cluster === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
							]"
						>
							<div class="flex w-full items-center space-x-2">
								<img :src="c.image" class="h-5 w-5" />
								<span class="text-sm font-medium">
									{{ c.title }}
								</span>
							</div>
						</button>
					</div>
				</div>
			</div>
			<div v-if="selectedVersion && cluster">
				<h2 class="text-sm font-medium leading-6 text-gray-900">Select Plan</h2>
				<div class="mt-2 overflow-hidden">
					<SitePlansCards v-model="plan" />
				</div>
			</div>
			<div v-if="selectedVersion && plan && cluster" class="w-1/2">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Enter Subdomain
				</h2>
				<div class="mt-2 items-center">
					<div class="col-span-2 flex w-full">
						<TextInput
							class="flex-1 rounded-r-none"
							placeholder="Subdomain"
							v-model="subdomain"
						/>
						<div class="flex items-center rounded-r bg-gray-100 px-4 text-base">
							.{{ options.domain }}
						</div>
					</div>
					<div
						v-if="$resources.subdomainExists.loading"
						class="text-base text-gray-600"
					>
						Checking...
					</div>
				</div>
				<div class="mt-1">
					<ErrorMessage :message="$resources.subdomainExists.error" />
					<template
						v-if="
							!$resources.subdomainExists.error &&
							$resources.subdomainExists.data != null
						"
					>
						<div
							v-if="$resources.subdomainExists.data"
							class="text-sm text-green-600"
						>
							{{ subdomain }}.{{ options.domain }} is available
						</div>
						<div v-else class="text-sm text-red-600">
							{{ subdomain }}.{{ options.domain }} is not available
						</div>
					</template>
				</div>
			</div>
			<div class="w-1/2" v-if="selectedVersion && cluster && plan">
				<h2 class="text-sm font-medium leading-6 text-gray-900">Summary</h2>
				<div
					class="mt-2 grid gap-x-4 gap-y-2 rounded-md border bg-gray-50 p-4 text-p-base"
					style="grid-template-columns: 1fr 4fr"
				>
					<div>Version:</div>
					<div class="font-medium">{{ selectedVersion.name }}</div>
					<div>Apps:</div>
					<div class="font-medium">
						{{
							selectedVersionApps
								.filter(app => apps.includes(app.app))
								.map(app => app.app_title)
								.join(', ')
						}}
					</div>
					<div>Plan:</div>
					<div v-if="selectedPlan">
						<div>
							<span class="font-medium">
								{{
									$format.userCurrency(
										$team.doc.currency == 'INR'
											? selectedPlan.price_inr
											: selectedPlan.price_usd
									)
								}}
								per month
							</span>
							<span class="text-gray-700" v-if="selectedPlan.support_included">
								(Support included)
							</span>
						</div>
						<div class="text-gray-700">
							{{
								$format.userCurrency(
									$team.doc.currency == 'INR'
										? selectedPlan.price_per_day_inr
										: selectedPlan.price_per_day_usd
								)
							}}
							per day
						</div>
					</div>
                    <div v-else>{{ plan }}</div>
					<div>Region:</div>
					<div class="font-medium">{{ selectedClusterTitle }}</div>
				</div>
			</div>
			<div
				v-if="selectedVersion && cluster && plan"
				class="flex w-1/2 flex-col space-y-4"
			>
				<FormControl
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me (${selectedClusterTitle}) shall stand applicable to me and Frappe.`"
				/>
				<FormControl
					type="checkbox"
					label="I am okay if my details are shared with local partner"
					@change="val => (shareDetailsConsent = val.target.checked)"
				/>
				<ErrorMessage class="my-2" :message="$resources.newSite.error" />
			</div>
			<div class="w-1/2" v-if="selectedVersion && cluster && plan">
				<Button
					class="w-full"
					variant="solid"
					@click="$resources.newSite.submit()"
					:loading="$resources.newSite.loading"
				>
					Create site
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import {
	Autocomplete,
	ErrorMessage,
	FeatherIcon,
	FormControl,
	TextInput,
	Tooltip,
	debounce,
	getCachedResource
} from 'frappe-ui';
import Header from '../components/Header.vue';
import { validateSubdomain } from '../../src/utils.js';
import router from '../router';
import SitePlansCards from '../components/SitePlansCards.vue';

// TODO:
// 1. Marketplace app plans
// 2. Restore from site, backup files

export default {
	name: 'NewSite',
	components: {
		FormControl,
		TextInput,
		Autocomplete,
		FeatherIcon,
		ErrorMessage,
		Header,
		SitePlansCards,
		Tooltip
	},
	data() {
		return {
			selectedVersion: null,
			subdomain: '',
			cluster: null,
			plan: null,
			apps: [],
			shareDetailsConsent: false,
			agreedToRegionConsent: false
		};
	},
	watch: {
		selectedVersion() {
			// reset all selections when version changes
			this.apps = [];
			this.cluster = null;
			this.agreedToRegionConsent = false;
		},
		subdomain: {
			handler: debounce(function (value) {
				let invalidMessage = validateSubdomain(value);
				this.$resources.subdomainExists.error = invalidMessage;
				if (!invalidMessage) {
					this.$resources.subdomainExists.submit();
				}
			}, 500)
		}
	},
	resources: {
		options() {
			return {
				url: 'press.api.site.options_for_new',
				cache: 'site.options_for_new',
				auto: true
			};
		},
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				params: {
					domain: this.options?.domain,
					subdomain: this.subdomain
				},
				validate() {
					return validateSubdomain(this.subdomain);
				},
				transform(data) {
					return !Boolean(data);
				}
			};
		},
		newSite() {
			if (!(this.options && this.selectedVersion)) return;
			let apps = ['frappe'].concat(this.apps);
			return {
				url: 'press.api.client.insert',
				params: {
					doc: {
						doctype: 'Site',
						team: this.$team.doc.name,
						subdomain: this.subdomain,
						apps: apps.map(app => ({ app })),
						cluster: this.cluster,
						bench: this.selectedVersion.group.bench,
						subscription_plan: this.plan,
						share_details_consent: this.shareDetailsConsent
					}
				},
				validate() {
					// let canCreate =
					// 	this.subdomainValid &&
					// 	this.selectedApps.length > 0 &&
					// 	this.selectedPlan &&
					// 	(!this.wantsToRestore || this.selectedFiles.database);

					if (!this.subdomain) {
						return 'Please enter a subdomain';
					}

					if (!this.agreedToRegionConsent) {
						return 'Please agree to the above consent to create site';
					}

					// if (!canCreate) {
					// 	return 'Cannot create site';
					// }
				},
				onSuccess: site => {
					router.push({
						name: 'Site Detail Jobs',
						params: { name: site.name }
					});
				}
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		selectedClusterTitle() {
			return this.selectedVersion?.group?.clusters?.find(
				c => c.name === this.cluster
			)?.title;
		},
		selectedVersionApps() {
			if (!this.selectedVersion?.group?.bench_app_sources) return [];
			// sorted by total installs and then by name
			return this.selectedVersion.group.bench_app_sources
				.map(app_source => {
					let app_source_details = this.options.app_source_details[app_source];
					let marketplace_details = app_source_details
						? this.options.marketplace_details[app_source_details.app]
						: {};
					return {
						app_title: app_source,
						...app_source_details,
						...marketplace_details
					};
				})
				.sort((a, b) => {
					if (a.total_installs > b.total_installs) {
						return -1;
					} else if (a.total_installs < b.total_installs) {
						return 1;
					} else {
						return a.app_title.localeCompare(b.app_title);
					}
				});
		},
		selectedPlan() {
			let plans = getCachedResource('site.plans');
			if (!plans?.data) return;
			return plans.data.find(p => p.name === this.plan);
		}
	},
	methods: {
		toggleApp(app) {
			if (app.app == 'frappe') {
				return;
			}
			if (this.apps.includes(app.app)) {
				this.apps = this.apps.filter(a => a !== app.app);
			} else {
				this.apps.push(app.app);
			}
		}
	}
};
</script>
