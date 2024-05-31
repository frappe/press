<template>
	<div class="top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[
					{
						label: 'Install App'
					}
				]"
			/>
		</Header>

		<div class="m-12 mx-auto max-w-2xl px-5">
			<div
				v-if="$resources.installAppOptions.loading"
				class="py-4 text-base text-gray-600"
			>
				Loading...
			</div>
			<div v-else class="space-y-6">
				<div class="mb-12 flex">
					<img
						:src="appDoc.image"
						class="h-12 w-12 rounded-lg border"
						:alt="appDoc.name"
					/>
					<div class="my-1 ml-4 flex flex-col justify-between">
						<h1 class="text-lg font-semibold">{{ appDoc.title }}</h1>
						<p class="text-sm text-gray-600">{{ appDoc.description }}</p>
					</div>
				</div>

				<div v-if="!options.is_app_featured && !options.private_groups.length">
					<div
						class="flex items-center space-x-2 rounded border border-gray-200 bg-gray-100 p-4 text-base text-gray-700"
					>
						<i-lucide-alert-circle class="inline-block h-5 w-5" />
						<p>
							This app isn't available in our public benches.<br />
							Read below documentation to add it to your own bench.
						</p>
					</div>
				</div>
				<div v-else class="space-y-12">
					<div v-if="plans.length">
						<div class="flex items-center justify-between">
							<h2 class="text-base font-medium leading-6 text-gray-900">
								Select Plan
							</h2>
						</div>
						<div class="mt-2">
							<PlansCards v-model="selectedPlan" :plans="plans" />
						</div>
					</div>

					<div v-if="options.private_groups.length">
						<h2 class="text-base font-medium leading-6 text-gray-900">
							Select Bench
							<span
								v-if="options.is_app_featured"
								class="text-sm text-gray-500"
							>
								(Optional)
							</span>
						</h2>
						<div class="mt-2 w-full space-y-2">
							<FormControl
								type="autocomplete"
								:options="
									options.private_groups.map(b => ({
										label: b.title,
										value: b.name
									}))
								"
								v-model="selectedGroup"
							/>
						</div>
					</div>

					<div
						v-if="
							options.is_app_featured ||
							(!options.is_app_featured && selectedGroup)
						"
					>
						<h2 class="text-base font-medium leading-6 text-gray-900">
							Select Region
						</h2>
						<div class="mt-2 w-full space-y-2">
							<div class="grid grid-cols-2 gap-3">
								<button
									v-for="c in regions"
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

					<div>
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
								<div
									class="flex items-center rounded-r bg-gray-100 px-4 text-base"
								>
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
					<div class="flex flex-col space-y-4">
						<FormControl
							class="checkbox"
							type="checkbox"
							v-model="agreedToRegionConsent"
							:label="`I agree that the laws of the region selected by me ${
								this.cluster ? `(${this.cluster})` : ''
							} shall stand applicable to me and Frappe.`"
						/>
						<ErrorMessage class="my-2" :message="$resources.newSite.error" />
						<Button
							class="w-full"
							variant="solid"
							:disabled="!agreedToRegionConsent"
							@click="$resources.newSite.submit()"
							:loading="$resources.newSite.loading"
						>
							Create site and install {{ appDoc.title }}
						</Button>
					</div>
				</div>
				<div class="flex space-x-1">
					<div class="text-sm text-gray-600">
						Want to install <b>{{ appDoc.title }}</b> on an existing Site/Bench?
					</div>
					<a
						class="text-sm underline"
						href="https://frappecloud.com/docs/installing-an-app"
						target="_blank"
					>
						Read documentation
					</a>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { Breadcrumbs, TextInput } from 'frappe-ui';
import { getDocResource } from '../utils/resource';
import Header from '../components/Header.vue';
import PlansCards from '../components/PlansCards.vue';

export default {
	name: 'InstallApp',
	props: {
		app: {
			type: String,
			required: true
		}
	},
	pageMeta() {
		return {
			title: `Install ${this.appDoc.title} - Frappe Cloud`
		};
	},
	components: {
		FBreadcrumbs: Breadcrumbs,
		PlansCards,
		Header
	},
	data() {
		return {
			plan: '',
			subdomain: '',
			cluster: null,
			selectedPlan: null,
			selectedGroup: null,
			agreedToRegionConsent: false
		};
	},
	resources: {
		installAppOptions() {
			return {
				url: 'press.api.marketplace.get_install_app_options',
				auto: true,
				params: {
					marketplace_app: this.app
				},
				initialData: {
					domain: '',
					plans: [],
					clusters: [],
					is_app_featured: false,
					private_groups: []
				},
				async onSuccess() {
					this.cluster = await this.getClosestCluster();
				}
			};
		},
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				makeParams() {
					return {
						domain: this.$resources.options.domain,
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
			if (!this.options) return;

			return {
				url: 'press.api.client.insert',
				makeParams() {
					return {
						doc: {
							doctype: 'Site',
							team: this.$team.doc.name,
							subdomain: this.subdomain,
							apps: [{ app: 'frappe' }, { app: this.app }],
							app_plans: this.selectedPlan
								? {
										[this.app]: this.selectedPlan
								  }
								: null,
							cluster: this.cluster,
							bench: this.regions.find(r => r.name === this.cluster).bench,
							group: this.selectedGroup?.value,
							subscription_plan: this.selectedGroup
								? this.options.private_site_plan
								: this.options.public_site_plan,
							domain: this.options.domain
						}
					};
				},
				validate() {
					if (!this.selectedPlan && this.plans.length > 0) {
						return 'Please select a plan';
					}
					if (!this.subdomain) {
						return 'Please enter a subdomain';
					}
					if (!this.agreedToRegionConsent) {
						return 'Please agree to the above consent to create site';
					}
				},
				onSuccess: site => {
					this.$router.push({
						name: 'Site Detail Jobs',
						params: { name: site.name }
					});
				}
			};
		}
	},
	methods: {
		async getClosestCluster() {
			if (this.closestCluster) return this.closestCluster;
			let proxyServers = this.options.clusters
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
				let closestCluster = this.options.clusters.find(
					c => c.proxy_server?.name === closestServer
				);
				if (!this.closestCluster) {
					this.closestCluster = closestCluster.name;
				}
				this.findingClosestServer = false;
			} else if (proxyServers.length === 1) {
				this.closestCluster = this.options.clusters[0].name;
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
		}
	},
	computed: {
		appDoc() {
			let doc = getDocResource({
				doctype: 'Marketplace App',
				name: this.app
			});
			return doc.doc || {};
		},
		options() {
			return this.$resources.installAppOptions.data;
		},
		plans() {
			return this.options.plans.map(plan => ({
				...plan,
				label:
					plan.price_inr === 0 || plan.price_usd === 0
						? 'Free'
						: `${this.$format.userCurrency(
								this.$team.doc.currency === 'INR'
									? plan.price_inr
									: plan.price_usd
						  )}/mo`,
				sublabel: ' ',
				features: plan.features.map(f => ({
					value: f,
					icon: 'check-circle'
				}))
			}));
		},
		regions() {
			if (!this.selectedGroup) {
				return this.options.clusters;
			} else {
				return this.options.private_groups.find(
					g => g.name === this.selectedGroup.value
				).clusters;
			}
		}
	}
};
</script>
