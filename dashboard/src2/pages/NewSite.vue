<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs :items="breadcrumbs" />
		</Header>
	</div>

	<div class="mx-auto max-w-2xl px-5">
		<div v-if="$resources.options.loading" class="py-4 text-base text-gray-600">
			Loading...
		</div>
		<div v-if="$route.name === 'NewBenchSite' && !bench">
			<div class="py-4 text-base text-gray-600">Something went wrong</div>
		</div>
		<div v-else-if="options" class="space-y-12 pb-[50vh] pt-12">
			<NewSiteAppSelector
				:availableApps="selectedVersionApps"
				:siteOnPublicBench="!bench"
				v-model="apps"
			/>
			<div v-if="!bench">
				<div class="flex items-center justify-between">
					<h2 class="text-base font-medium leading-6 text-gray-900">
						Select Frappe Framework Version
					</h2>
				</div>
				<div class="mt-2">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
						<button
							v-for="v in availableVersions"
							:key="v.name"
							:class="[
								version === v.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  hover:bg-gray-50',
								v.disabled && 'pointer-events-none opacity-50',
								'flex cursor-pointer items-center justify-between rounded border border-gray-400 p-3 text-sm focus:outline-none'
							]"
							@click="version = v.name"
						>
							<span class="font-medium">{{ v.name }} </span>
							<span class="ml-1 text-gray-600">
								{{ v.status }}
							</span>
						</button>
					</div>
				</div>
			</div>
			<div
				class="flex flex-col"
				v-if="selectedVersion?.group?.clusters?.length"
			>
				<h2 class="text-base font-medium leading-6 text-gray-900">
					Select Region
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3">
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
							<div class="flex w-full items-center justify-between">
								<div class="flex w-full items-center space-x-2">
									<img :src="c.image" class="h-5 w-5" />
									<span class="text-sm font-medium">
										{{ c.title }}
									</span>
								</div>
								<Badge v-if="c.beta" :label="c.beta ? 'Beta' : ''" />
							</div>
						</button>
					</div>
				</div>
			</div>
			<div v-if="selectedVersion && cluster">
				<div class="flex items-center justify-between">
					<h2 class="text-base font-medium leading-6 text-gray-900">
						Select Plan
					</h2>
					<div>
						<Button link="https://frappecloud.com/pricing" variant="ghost">
							<template #prefix>
								<i-lucide-help-circle class="h-4 w-4 text-gray-700" />
							</template>
							Help
						</Button>
					</div>
				</div>
				<div class="mt-2">
					<SitePlansCards
						v-model="plan"
						:isBenchSite="!!bench"
						:isDedicatedServerSite="selectedVersion.group.is_dedicated_server"
					/>
				</div>
			</div>
			<div v-if="selectedVersion && plan && cluster">
				<h2 class="text-base font-medium leading-6 text-gray-900">
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
			<Summary
				v-if="selectedVersion && cluster && plan && subdomain"
				:options="siteSummaryOptions"
			/>
			<div
				v-if="selectedVersion && cluster && plan"
				class="flex flex-col space-y-4"
			>
				<FormControl
					class="checkbox"
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me (${selectedClusterTitle}) shall stand applicable to me and Frappe.`"
				/>
				<FormControl
					class="checkbox"
					type="checkbox"
					label="I am okay if my details are shared with local partner"
					@change="val => (shareDetailsConsent = val.target.checked)"
				/>
				<ErrorMessage class="my-2" :message="$resources.newSite.error" />
			</div>
			<div v-if="selectedVersion && cluster && plan && subdomain">
				<Button
					class="w-full"
					variant="solid"
					:disabled="!agreedToRegionConsent"
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
	Breadcrumbs,
	getCachedDocumentResource
} from 'frappe-ui';
import SitePlansCards from '../components/SitePlansCards.vue';
import { validateSubdomain } from '../../src/utils.js';
import Header from '../components/Header.vue';
import router from '../router';
import { plans } from '../data/plans';
import NewSiteAppSelector from '../components/site/NewSiteAppSelector.vue';
import Summary from '../components/Summary.vue';

export default {
	name: 'NewSite',
	props: ['bench'],
	components: {
		FBreadcrumbs: Breadcrumbs,
		NewSiteAppSelector,
		SitePlansCards,
		Autocomplete,
		ErrorMessage,
		FormControl,
		FeatherIcon,
		TextInput,
		Tooltip,
		Summary,
		Header
	},
	data() {
		return {
			version: null,
			subdomain: '',
			cluster: null,
			plan: null,
			apps: [],
			appPlans: {},
			selectedApp: null,
			closestCluster: null,
			showAppPlanSelectorDialog: false,
			shareDetailsConsent: false,
			agreedToRegionConsent: false
		};
	},
	watch: {
		apps() {
			this.version = this.autoSelectVersion();
			this.agreedToRegionConsent = false;
		},
		async version() {
			this.cluster = await this.getClosestCluster();
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
		},
		closestCluster() {
			this.cluster = this.closestCluster;
		}
	},
	resources: {
		options() {
			return {
				url: 'press.api.site.options_for_new',
				makeParams() {
					return { for_bench: this.bench };
				},
				onSuccess() {
					if (this.bench) {
						this.version = this.options.versions[0].name;
					}
				},
				auto: true
			};
		},
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				makeParams() {
					return {
						domain: this.options?.domain,
						subdomain: this.subdomain
					};
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

			return {
				url: 'press.api.client.insert',
				makeParams() {
					let appPlans = {};
					for (let app of this.apps) {
						if (app.plan) {
							appPlans[app.app] = app.plan;
						}
					}

					return {
						doc: {
							doctype: 'Site',
							team: this.$team.doc.name,
							subdomain: this.subdomain,
							apps: [
								{ app: 'frappe' },
								...this.apps
									.filter(app => app.app)
									.map(app => ({ app: app.app }))
							],
							app_plans: appPlans,
							cluster: this.cluster,
							bench: this.selectedVersion.group.bench,
							subscription_plan: this.plan.name,
							share_details_consent: this.shareDetailsConsent
						}
					};
				},
				validate() {
					if (!this.subdomain) {
						return 'Please enter a subdomain';
					}

					if (!this.agreedToRegionConsent) {
						return 'Please agree to the above consent to create site';
					}
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
		selectedVersion() {
			return this.options?.versions.find(v => v.name === this.version);
		},
		availableVersions() {
			if (!this.apps.length || this.bench)
				return this.options.versions.sort((a, b) =>
					b.name.localeCompare(a.name)
				);

			let commonVersions = this.apps.reduce((acc, app) => {
				if (!acc) return app.sources.map(s => s.version);
				return acc.filter(v => app.sources.map(s => s.version).includes(v));
			}, null);

			return this.options.versions.map(v => ({
				...v,
				disabled: !commonVersions.includes(v.name)
			}));
		},
		selectedClusterTitle() {
			return this.selectedVersion?.group?.clusters?.find(
				c => c.name === this.cluster
			)?.title;
		},
		selectedVersionApps() {
			let apps = [];

			if (!this.bench)
				apps = this.options.app_source_details.sort((a, b) =>
					a.total_installs !== b.total_installs
						? b.total_installs - a.total_installs
						: a.app.localeCompare(b.app)
				);
			else if (!this.selectedVersion?.group?.bench_app_sources) apps = [];
			else
				apps = this.selectedVersion.group.bench_app_sources.map(app_source => {
					let app_source_details = this.options.app_source_details[app_source];
					let marketplace_details = app_source_details
						? this.options.marketplace_details[app_source_details.app]
						: {};
					return {
						app_title: app_source,
						...app_source_details,
						...marketplace_details
					};
				});

			// sorted by total installs and then by name
			return apps.sort((a, b) => {
				if (a.total_installs > b.total_installs) {
					return -1;
				} else if (a.total_installs < b.total_installs) {
					return 1;
				} else {
					return a.app_title.localeCompare(b.app_title);
				}
			});
		},
		selectedVersionPublicApps() {
			return this.selectedVersionApps.filter(app => app.public);
		},
		selectedVersionPrivateApps() {
			if (this.selectedVersion?.group?.public) return [];

			return this.selectedVersionApps.filter(app => !app.public);
		},
		selectedPlan() {
			if (!plans?.data) return;
			return plans.data.find(p => p.name === this.plan.name);
		},
		breadcrumbs() {
			if (this.bench) {
				let group = getCachedDocumentResource('Release Group', this.bench);
				return [
					{ label: 'Benches', route: '/benches' },
					{
						label: group ? group.doc.title : this.bench,
						route: {
							name: 'Release Group Detail',
							params: { name: this.bench }
						}
					},
					{
						label: 'New Site',
						route: { name: 'Bench New Site', params: { bench: this.bench } }
					}
				];
			}
			return [
				{ label: 'Sites', route: '/sites' },
				{ label: 'New Site', route: '/sites/new' }
			];
		},
		_totalPerMonth() {
			let total =
				this.$team.doc.currency == 'INR'
					? this.selectedPlan.price_inr
					: this.selectedPlan.price_usd;

			for (let app of this.apps.filter(app => app.plan)) {
				total +=
					this.$team.doc.currency == 'INR'
						? app.plan.price_inr
						: app.plan.price_usd;
			}

			return total;
		},
		totalPerMonth() {
			return this.$format.userCurrency(this._totalPerMonth);
		},
		totalPerDay() {
			return this.$format.userCurrency(
				this.$format.pricePerDay(this._totalPerMonth)
			);
		},
		siteSummaryOptions() {
			let appPlans = [];
			for (let app of this.apps) {
				appPlans.push(
					`${this.selectedVersionApps.find(a => a.app === app.app).app_title} ${
						app.plan?.price_inr
							? `- <span class="text-gray-600">${this.$format.userCurrency(
									this.$team.doc.currency == 'INR'
										? app.plan.price_inr
										: app.plan.price_usd
							  )} per month</span>`
							: ''
					}`
				);
			}

			return [
				{
					label: 'Frappe Framework Version',
					value: this.selectedVersion?.name
				},
				{
					label: 'Region',
					value: this.selectedClusterTitle
				},
				{
					label: 'Site URL',
					value: `${this.subdomain}.${this.options?.domain}`
				},
				{
					label: 'Site Plan',
					value: `${this.$format.userCurrency(
						this.$team.doc.currency == 'INR'
							? this.selectedPlan.price_inr
							: this.selectedPlan.price_usd
					)} per month`
				},
				{
					label: 'Product Warranty',
					value: this.selectedPlan.support_included
						? 'Included'
						: 'Not Included'
				},
				{
					label: 'Apps',
					value: this.apps.length ? appPlans.join('<br>') : 'No apps selected'
				},
				{
					label: 'Total',
					value: `${this.totalPerMonth} per month <div class="text-gray-600">${this.totalPerDay} per day</div>`,
					condition: () => this._totalPerMonth
				}
			];
		}
	},
	methods: {
		async getClosestCluster() {
			if (this.closestCluster) return this.closestCluster;
			let proxyServers = this.selectedVersion?.group?.clusters
				.flatMap(c => c.proxy_server || [])
				.map(server => server.name);

			if (proxyServers.length > 0) {
				this.findingClosestServer = true;
				let promises = proxyServers.map(server => this.getPingTime(server));
				let results = await Promise.allSettled(promises);
				let fastestServer = results.reduce((a, b) =>
					a.value.pingTime < b.value.pingTime ? a : b
				);
				let closestServer = fastestServer.value.server;
				let closestCluster = this.selectedVersion?.group?.clusters.find(
					c => c.proxy_server?.name === closestServer
				);
				if (!this.closestCluster) {
					this.closestCluster = closestCluster.name;
				}
				this.findingClosestServer = false;
			} else if (proxyServers.length === 1) {
				this.closestCluster = this.selectedVersion?.group?.clusters[0].name;
			}
			return this.closestCluster;
		},
		async getPingTime(server) {
			let pingTime = 999999;
			try {
				let t1 = new Date().getTime();
				let r = await fetch(`https://${server}`);
				let t2 = new Date().getTime();
				pingTime = t2 - t1;
			} catch (error) {
				console.warn(error);
			}
			return { server, pingTime };
		},
		autoSelectVersion() {
			if (!this.availableVersions) return null;

			return this.availableVersions
				.sort((a, b) => b.name.localeCompare(a.name))
				.find(v => !v.disabled)?.name;
		}
	}
};
</script>
<style scoped>
.checkbox:deep(label) {
	color: theme('colors.gray.700') !important;
	line-height: 1.5;
}
</style>
