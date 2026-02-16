<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs :items="breadcrumbs" />
		</Header>
	</div>

	<div
		v-if="!$team.doc?.is_desk_user && !$session.hasSiteCreationAccess"
		class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
	>
		<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
		<ErrorMessage message="You aren't permitted to create new sites" />
	</div>

	<div v-else class="mx-auto max-w-2xl px-5">
		<div v-if="$resources.options.loading" class="py-4 text-base text-gray-600">
			Loading...
		</div>
		<div v-if="$route.name === 'NewBenchSite' && !bench">
			<div class="py-4 text-base text-gray-600">Something went wrong</div>
		</div>
		<div v-else-if="options" class="space-y-12 pb-[50vh] pt-12">
			<NewSiteAppSelector
				:availableApps="selectedVersionAppOptions"
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
						<component
							v-for="v in availableVersions"
							:key="v.name"
							:is="v.disabled ? 'Tooltip' : 'div'"
							:text="
								v.disabled && versionAppsMap[v.name]
									? `This version is not available for the ${$format.plural(
											versionAppsMap[v.name].length,
											'app',
											'apps',
										)} ${$format.commaAnd(versionAppsMap[v.name])}`
									: ''
							"
						>
							<button
								:class="[
									version === v.name
										? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
										: 'bg-white text-gray-900  hover:bg-gray-50',
									v.disabled && 'opacity-50 hover:cursor-default',
									'flex w-full cursor-pointer items-center justify-between rounded border border-gray-400 p-3 text-sm focus:outline-none',
								]"
								@click="
									() => {
										if (v.disabled) return;
										version = v.name;
									}
								"
							>
								<span class="font-medium">{{ v.name }} </span>
								<div
									v-if="v.status === 'Develop'"
									class="flex items-center gap-2"
								>
									<Tooltip
										text="This version is under development and may have bugs. Do not use for production sites."
									>
										<lucide-info class="h-4 w-4 text-gray-500" />
									</Tooltip>
									<span class="ml-1 text-gray-600">
										{{ v.status }}
									</span>
								</div>
							</button>
						</component>
					</div>
				</div>
			</div>
			<div v-if="showLocalisationSelector" class="space-y-4">
				<div class="flex space-x-2">
					<FormControl
						label="Install Local Compliance App?"
						v-model="showLocalisationOption"
						type="checkbox"
					/>
					<Tooltip
						text="A local compliance app allows creating transactions as per statutory compliance. They're maintained by community partners."
					>
						<lucide-info class="h-4 w-4 text-gray-500" />
					</Tooltip>
				</div>
				<FormControl
					class="w-1/2"
					variant="outline"
					:class="{ 'pointer-events-none opacity-50': !showLocalisationOption }"
					label="Select Country"
					:modelValue="selectedLocalisationCountry?.value"
					@update:modelValue="
						selectedLocalisationCountry = localisationAppCountries.find(
							(option) => option.value === $event,
						)
					"
					type="combobox"
					:options="localisationAppCountries"
				/>
			</div>
			<div
				v-if="
					bench &&
					(showDedicatedServerOption ||
						dedicatedServerConfig?.case === 'dedicated_only_multiple')
				"
				class="space-y-4"
			>
				<FormControl
					v-if="dedicatedServerConfig?.case != 'dedicated_only_multiple'"
					type="checkbox"
					v-model="useDedicatedServer"
					label="Host this site on your dedicated server"
				/>
				<div v-if="shouldShowDedicatedServerDropdown">
					<h2 class="text-base font-medium leading-6 text-gray-900 mb-2">
						Select Dedicated Server
					</h2>
					<FormControl
						required
						v-model="selectedDedicatedServer"
						type="select"
						class="w-1/2"
						:options="
							availableDedicatedServers.map((s) => ({
								label: s.title,
								value: s.name,
							}))
						"
					/>
				</div>
			</div>
			<div
				v-if="
					!this.selectedDedicatedServer &&
					selectedVersion &&
					options.providers?.length
				"
				class="flex flex-col"
			>
				<h2 class="text-base font-medium leading-6 text-gray-900">
					Select Provider
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3">
						<button
							v-for="p in options.providers"
							:key="p.name"
							@click="provider = p.name"
							:class="[
								provider === p.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
								'flex w-full items-center rounded-md border p-2 text-left text-base text-gray-900',
							]"
						>
							<div class="flex w-full items-center justify-between">
								<div class="flex w-full items-center space-x-2">
									<img
										v-if="p.image"
										:src="p.image"
										class="h-5 w-5 rounded-sm"
									/>
									<span class="text-sm font-medium">
										{{ p.title }}
									</span>
								</div>
							</div>
						</button>
					</div>
				</div>
			</div>
			<div
				class="flex flex-col"
				v-if="
					!this.selectedDedicatedServer &&
					selectedVersion?.group &&
					filteredClusters.length &&
					(provider || bench)
				"
			>
				<h2 class="text-base font-medium leading-6 text-gray-900">
					Select Region
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3">
						<button
							v-for="c in filteredClusters"
							:key="c.name"
							@click="cluster = c.name"
							:class="[
								cluster === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'bg-white text-gray-900  hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
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
								<lucide-help-circle class="h-4 w-4 text-gray-700" />
							</template>
							Help
						</Button>
					</div>
				</div>
				<div class="mt-2">
					<SitePlansCards
						v-model="plan"
						:isPrivateBenchSite="!!bench"
						:isDedicatedServerSite="isDedicatedServerSite"
						:selectedCluster="cluster"
						:selectedApps="apps"
						:selectedVersion="version"
						:selectedProvider="effectiveProvider"
						:hideRestrictedPlans="selectedLocalisationCountry"
					/>
				</div>
				<div v-if="isPrivateBenchPlan" class="mt-4 text-xs text-gray-700">
					<div
						class="flex items-center rounded bg-blue-50 p-2 text-p-base font-medium text-blue-800"
					>
						<lucide-info class="h-4 w-8 text-blue-600" />
						<span class="ml-4">
							Your site will be created on a
							<strong>private bench</strong>.<br />You can install custom apps
							and have full control over the bench.
						</span>
					</div>
				</div>
				<div class="mt-4 text-xs text-gray-700">
					<div
						class="flex items-center rounded bg-gray-50 p-2 text-p-base font-medium text-gray-800"
					>
						<lucide-badge-check class="h-4 w-8 text-gray-600" />
						<span class="ml-4">
							<strong>Support</strong> covers only issues of Frappe apps and not
							functional queries. You can raise a support ticket for Frappe
							Cloud issues for all plans.
						</span>
					</div>
				</div>
			</div>
			<div v-if="selectedVersion && plan && cluster">
				<div class="flex justify-between items-center">
					<h2 class="text-base font-medium leading-6 text-gray-900">
						Enter Subdomain
					</h2>
					<Tooltip
						v-if="this.domain !== this.options.domain"
						text="The root domain can change depending on the region you choose"
					>
						<lucide-help-circle class="h-4 w-4 text-gray-500" />
					</Tooltip>
				</div>
				<div class="mt-2 items-center">
					<div class="col-span-2 flex w-full">
						<input
							class="dark:[color-scheme:dark] z-10 h-7 w-full flex-1 rounded rounded-r-none border border-[--surface-gray-2] bg-surface-gray-2 py-1.5 pl-2 pr-2 text-base text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-modals hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							placeholder="Subdomain"
							v-model="subdomain"
						/>
						<div class="flex items-center rounded-r bg-gray-100 px-4 text-base">
							.{{ domain }}
						</div>
					</div>
				</div>
				<div class="mt-1">
					<div
						v-if="$resources.subdomainExists.loading"
						class="text-base text-gray-600"
					>
						Checking...
					</div>
					<template
						v-else-if="
							!$resources.subdomainExists.error &&
							$resources.subdomainExists.data != null
						"
					>
						<div
							v-if="$resources.subdomainExists.data"
							class="text-sm text-green-600"
						>
							{{ subdomain }}.{{ domain }} is available
						</div>
						<div v-else class="text-sm text-red-600">
							{{ subdomain }}.{{ domain }} is not available
						</div>
					</template>
					<ErrorMessage :message="$resources.subdomainExists.error" />
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
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me (${selectedClusterTitle}) shall stand applicable to me and Frappe.`"
				/>
				<FormControl
					class="checkbox"
					type="checkbox"
					label="I am okay if my details are shared with local partner"
					@change="(val) => (shareDetailsConsent = val.target.checked)"
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
					:loadingText="
						isPrivateBenchPlan
							? 'Provisioning private bench and creating site...'
							: 'Creating site... This may take a while...'
					"
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
	getCachedDocumentResource,
	Badge,
} from 'frappe-ui';
import SitePlansCards from '../components/SitePlansCards.vue';
import { validateSubdomain } from '../utils/site';
import Header from '../components/Header.vue';
import router from '../router';
import { plans } from '../data/plans';
import NewSiteAppSelector from '../components/site/NewSiteAppSelector.vue';
import Summary from '../components/Summary.vue';
import { DashboardError } from '../utils/error';
import { getCountry } from '../utils/country';

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
		Header,
		Badge,
	},
	data() {
		return {
			version: null,
			subdomain: '',
			cluster: null,
			provider: null,
			plan: null,
			apps: [],
			appPlans: {},
			selectedApp: null,
			closestCluster: null,
			selectedLocalisationCountry: null,
			showLocalisationOption: false,
			showAppPlanSelectorDialog: false,
			shareDetailsConsent: false,
			agreedToRegionConsent: false,
			useDedicatedServer: false,
			selectedDedicatedServer: null,
		};
	},
	watch: {
		apps() {
			if (!(this.bench && this.selectedDedicatedServer)) {
				this.version = this.autoSelectVersion();
				this.cluster = null;
			}
			this.agreedToRegionConsent = false;
		},
		showLocalisationOption() {
			if (this.showLocalisationOption) {
				const localisationAppCountries = this.localisationAppCountries.map(
					(c) => c.value,
				);

				if (
					localisationAppCountries.includes(getCountry()) &&
					!this.selectedLocalisationCountry
				) {
					this.selectedLocalisationCountry = { value: getCountry() };
				}
			} else {
				this.selectedLocalisationCountry = null;
			}
		},
		version() {
			this.cluster = null;
			this.provider = null;
			this.agreedToRegionConsent = false;
			// Reset localisation selection when version changes
			this.selectedLocalisationCountry = null;
			this.showLocalisationOption = false;
		},
		provider() {
			if (this.bench) {
				// provider is inferred from cluster selection, so avoid clearing it
				return;
			}

			this.cluster = null;
			this.plan = null;
			this.agreedToRegionConsent = false;
		},
		cluster() {
			this.plan = null;
			this.agreedToRegionConsent = false;

			// For bench flow, set provider based on the selected cluster's cloud_provider
			if (this.bench && this.cluster) {
				const selectedCluster = this.selectedVersion?.group?.clusters.find(
					(c) => c.name === this.cluster,
				);
				if (selectedCluster?.cloud_provider) {
					this.provider = selectedCluster.cloud_provider;
				}
			}
		},
		useDedicatedServer(newVal) {
			if (newVal && this.availableDedicatedServers.length === 1) {
				const server = this.availableDedicatedServers[0];
				this.selectedDedicatedServer = server.name;
				this.cluster = server.cluster;
				this.provider = server.provider;
			} else {
				this.selectedDedicatedServer = null;
				this.cluster = null;
				this.provider = null;
			}
		},
		selectedDedicatedServer(newServer) {
			if (!newServer) return;
			const server = this.availableDedicatedServers.find(
				(s) => s.name === newServer,
			);
			if (server) {
				this.cluster = server.cluster;
				this.provider = server.provider;
			}
		},
		subdomain: {
			handler: debounce(function (value) {
				let invalidMessage = validateSubdomain(value);
				this.$resources.subdomainExists.error = invalidMessage;
				if (!invalidMessage) {
					this.$resources.subdomainExists.submit();
				}
			}, 500),
		},
	},
	resources: {
		options() {
			return {
				url: 'press.api.site.options_for_new',
				makeParams() {
					return { for_bench: this.bench };
				},
				onSuccess() {
					this.closestCluster = this.options.closest_cluster;
					if (this.bench && this.options.versions.length > 0) {
						this.version = this.options.versions[0].name;

						this.$nextTick(() => {
							const config = this.dedicatedServerConfig;
							if (!config || !config.dedicated_servers) return;

							if (config.case === 'dedicated_only_single') {
								this.useDedicatedServer = true;
								const server = config.dedicated_servers[0];
								this.cluster = server.cluster;
								this.provider = server.provider;
								this.selectedDedicatedServer = server.name;
							} else if (config.case === 'dedicated_only_multiple') {
								this.useDedicatedServer = true;
							}
						});
					}
				},
				auto: true,
			};
		},
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				makeParams() {
					return {
						domain: this.domain,
						subdomain: this.subdomain,
					};
				},
				validate() {
					let error = validateSubdomain(this.subdomain);
					if (error) {
						return new DashboardError(error);
					}
				},
				transform(data) {
					return !Boolean(data);
				},
			};
		},
		newSite() {
			if (!(this.options && this.selectedVersion)) return;

			if (this.bench) {
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
										.filter((app) => app.app)
										.map((app) => ({ app: app.app })),
								],
								app_plans: appPlans,
								cluster: this.cluster,
								group: this.selectedVersion.group.name,
								domain: this.domain,
								subscription_plan: this.plan.name,
								share_details_consent: this.shareDetailsConsent,
								server: this.selectedDedicatedServer || null,
							},
						};
					},
					validate() {
						if (this.useDedicatedServer && !this.selectedDedicatedServer) {
							throw new DashboardError(
								'Please select a dedicated server to deploy your site.',
							);
						}
						if (!this.subdomain) {
							throw new DashboardError('Please enter a subdomain');
						}

						if (!this.agreedToRegionConsent) {
							throw new DashboardError(
								'Please agree to the above consent to create site',
							);
						}
					},
					onSuccess: (site) => {
						router.push({
							name: 'Site Jobs',
							params: { name: site.name },
						});
					},
				};
			} else {
				return {
					url: 'press.api.site.new',
					makeParams() {
						let appPlans = {};
						for (let app of this.apps) {
							if (app.plan) {
								appPlans[app.app] = app.plan;
							}
						}

						return {
							site: {
								name: this.subdomain,
								apps: ['frappe', ...this.apps.map((app) => app.app)],
								localisation_country: this.showLocalisationSelector
									? this.selectedLocalisationCountry?.value
									: null,
								version: this.selectedVersion.name,
								provider: this.provider,
								group: this.selectedVersion.group.name,
								cluster: this.cluster,
								plan: this.plan.name,
								share_details_consent: this.shareDetailsConsent,
								selected_app_plans: appPlans,
								domain: this.domain,
								// files: this.selectedFiles,
								// skip_failing_patches: this.skipFailingPatches,
							},
						};
					},
					validate() {
						if (!this.subdomain) {
							throw new DashboardError('Please enter a subdomain');
						}

						if (!this.agreedToRegionConsent) {
							throw new DashboardError(
								'Please agree to the above consent to create site',
							);
						}
					},
					onSuccess: (response) => {
						if (response.site_group_deploy) {
							router.push({
								name: 'NewSiteProgress',
								params: { siteGroupDeployName: response.site_group_deploy },
							});
						} else {
							router.push({
								name: 'Site Job',
								params: { name: response.site, id: response.job },
							});
						}
					},
				};
			}
		},
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		domain() {
			return (
				this.options?.cluster_specific_root_domains?.find(
					(d) => d.cluster === this.cluster,
				)?.name || this.options?.domain
			);
		},
		selectedVersion() {
			return this.options?.versions.find((v) => v.name === this.version);
		},
		dedicatedServerConfig() {
			if (!this.bench) return {};
			return this.selectedVersion?.group?.dedicated_server_config || {};
		},
		showDedicatedServerOption() {
			const case_type = this.dedicatedServerConfig?.case || '';
			return (
				case_type === 'user_choice_single' ||
				case_type === 'user_choice_multiple'
			);
		},
		isDedicatedServerSite() {
			return this.useDedicatedServer && this.selectedDedicatedServer;
		},
		availableDedicatedServers() {
			return this.dedicatedServerConfig?.dedicated_servers || [];
		},
		shouldShowDedicatedServerDropdown() {
			const case_type = this.dedicatedServerConfig?.case;
			const hasMultipleServers = this.availableDedicatedServers.length > 1;
			// Only show server selection when:
			// 1. user_choice_multiple - User has enabled dedicated server checkbox AND there are multiple servers
			// 2. dedicated_only_multiple - bench group has multiple dedicated servers linked to it and none public
			if (!this.useDedicatedServer || !hasMultipleServers) {
				return false;
			}

			return (
				case_type === 'user_choice_multiple' ||
				case_type === 'dedicated_only_multiple'
			);
		},
		availableVersions() {
			if (!this.apps.length || this.bench)
				return (this.options?.versions || []).sort((a, b) =>
					b.name.localeCompare(a.name),
				);

			let commonVersions = this.apps.reduce((acc, app) => {
				if (!acc) return app.sources.map((s) => s.version);
				return acc.filter((v) => app.sources.map((s) => s.version).includes(v));
			}, null);

			return (this.options?.versions || []).map((v) => ({
				...v,
				disabled: !commonVersions.includes(v.name),
			}));
		},
		selectedClusterTitle() {
			const allClusters = [
				...(this.selectedVersion?.group?.clusters || []),
				...(this.options.additional_clusters || []),
			];
			return allClusters.find((c) => c.name === this.cluster)?.title;
		},
		filteredClusters() {
			if (!this.selectedVersion?.group?.clusters) return [];

			const versionClusters = this.selectedVersion.group.clusters;

			if (!this.provider) return versionClusters;

			// version clusters with additional private bench clusters
			const allClusters = [
				...versionClusters,
				...(this.options?.additional_clusters || []),
			];

			return allClusters.filter((c) => c.cloud_provider === this.provider);
		},
		selectedClusterProvider() {
			if (!this.cluster) return null;
			const versionClusters = this.selectedVersion?.group?.clusters || [];
			const clusterDetails = versionClusters.find(
				(c) => c.name === this.cluster,
			);
			return clusterDetails?.cloud_provider || null;
		},
		effectiveProvider() {
			return this.provider || this.selectedClusterProvider;
		},
		selectedVersionApps() {
			let apps = [];

			if (!this.bench)
				apps = (this.options?.app_source_details || []).sort((a, b) =>
					a.total_installs !== b.total_installs
						? b.total_installs - a.total_installs
						: a.app.localeCompare(b.app),
				);
			else if (!this.selectedVersion?.group?.bench_app_sources) apps = [];
			else
				apps = this.selectedVersion.group.bench_app_sources.map(
					(app_source) => {
						let app_source_details =
							this.options?.app_source_details?.[app_source];

						let marketplace_details = app_source_details
							? this.options?.marketplace_details?.[app_source_details.app] ||
								{}
							: {};

						return {
							app_title: app_source,
							...app_source_details,
							...marketplace_details,
						};
					},
				);

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
		selectedVersionAppOptions() {
			return this.selectedVersionApps.filter(
				(app) => !this.localisationAppNames.includes(app.app),
			);
		},
		isPrivateBenchPlan() {
			return !this.bench && Boolean(this.plan?.private_bench_support);
		},
		showLocalisationSelector() {
			if (
				!this.selectedVersionApps ||
				!this.localisationAppNames.length ||
				!this.apps.length ||
				!this.version
			)
				return false;

			// Check if there are any localisation countries available for the selected version
			if (!this.localisationAppCountries.length) return false;

			const appsThatNeedLocalisation = this.selectedVersionApps.filter(
				(app) => app.localisation_apps.length,
			);

			if (
				appsThatNeedLocalisation.some((app) =>
					this.apps.map((a) => a.app).includes(app.app),
				)
			)
				return true;

			return false;
		},
		localisationAppNames() {
			if (!this.selectedVersionApps) return [];
			const localisationAppDetails = this.selectedVersionApps.flatMap(
				(app) => app.localisation_apps,
			);

			return localisationAppDetails
				.map((app) => app?.marketplace_app)
				.filter(Boolean);
		},
		localisationAppCountries() {
			if (!this.selectedVersionApps || !this.selectedVersion) return [];

			// Get the bench_app_sources for the selected version
			const versionAppSources =
				this.selectedVersion?.group?.bench_app_sources || [];

			// Get all localisation app details from selected apps
			const localisationAppDetails = this.selectedVersionApps.flatMap(
				(app) => app.localisation_apps,
			);

			// Filter to only include countries whose localisation app is available in the selected version
			return localisationAppDetails
				.filter((app) => {
					if (!app?.marketplace_app) return false;
					// Check if this localisation app has a source in the selected version's bench_app_sources
					return versionAppSources.some((source) =>
						source.toLowerCase().includes(app.marketplace_app.toLowerCase()),
					);
				})
				.map((app) => ({
					label: app?.country,
					value: app?.country,
				}))
				.sort((a, b) => a.label.localeCompare(b.label));
		},
		selectedPlan() {
			if (!plans?.data) return;
			return plans.data.find((p) => p.name === this.plan.name);
		},
		versionAppsMap() {
			const versions = this.availableVersions.map((v) => v.name);
			let problemAppVersions = {};
			if (!this.bench)
				for (let app of this.apps) {
					const appVersions = app.sources.map((s) => s.version);
					const problemVersions = versions.filter(
						(version) => !appVersions.includes(version),
					);
					for (let version of problemVersions) {
						if (!problemAppVersions[version]) {
							problemAppVersions[version] = [];
						}
						problemAppVersions[version].push(app.app_title);
					}
				}
			return problemAppVersions;
		},
		breadcrumbs() {
			if (this.bench) {
				let group = getCachedDocumentResource('Release Group', this.bench);
				return [
					{ label: 'Bench Groups', route: '/groups' },
					{
						label: group ? group.doc.title : this.bench,
						route: {
							name: 'Release Group Detail',
							params: { name: this.bench },
						},
					},
					{
						label: 'New Site',
						route: {
							name: 'Release Group New Site',
							params: { bench: this.bench },
						},
					},
				];
			}
			return [
				{ label: 'Sites', route: '/sites' },
				{ label: 'New Site', route: '/sites/new' },
			];
		},
		_totalPerMonth() {
			let total =
				this.$team.doc.currency == 'INR'
					? this.selectedPlan.price_inr
					: this.selectedPlan.price_usd;

			for (let app of this.apps.filter((app) => app.plan)) {
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
				this.$format.pricePerDay(this._totalPerMonth),
			);
		},
		siteSummaryOptions() {
			let appPlans = [];
			for (let app of this.apps) {
				appPlans.push(
					`${
						this.selectedVersionApps.find((a) => a.app === app.app).app_title
					} ${
						app.plan?.price_inr
							? `- <span class="text-gray-600">${this.$format.userCurrency(
									this.$team.doc.currency == 'INR'
										? app.plan.price_inr
										: app.plan.price_usd,
								)} per month</span>`
							: ''
					}`,
				);
			}

			return [
				{
					label: 'Frappe Framework Version',
					value: this.selectedVersion?.name,
				},
				{
					label: 'Region',
					value: this.selectedClusterTitle,
				},
				{
					label: 'Site URL',
					value: `${this.subdomain}.${this.domain}`,
				},
				{
					label: 'Site Plan',
					value: `${this.$format.userCurrency(
						this.$team.doc.currency == 'INR'
							? this.selectedPlan.price_inr
							: this.selectedPlan.price_usd,
					)} per month`,
				},
				{
					label: 'Product Warranty',
					value: this.selectedPlan.support_included
						? 'Included'
						: 'Not Included',
				},
				{
					label: 'Apps',
					value: this.apps.length ? appPlans.join('<br>') : 'No apps selected',
				},
				{
					label: 'Total',
					value: `${this.totalPerMonth} per month <div class="text-gray-600">${this.totalPerDay} per day</div>`,
					condition: () => this._totalPerMonth,
				},
			];
		},
	},
	methods: {
		autoSelectVersion() {
			if (!this.availableVersions) return null;

			return this.availableVersions
				.sort((a, b) => b.name.localeCompare(a.name))
				.find((v) => !v.disabled)?.name;
		},
	},
};
</script>
<style scoped>
.checkbox:deep(label) {
	color: theme('colors.gray.700') !important;
	line-height: 1.5;
}
</style>
