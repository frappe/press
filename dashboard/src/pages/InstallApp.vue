<template>
	<div class="top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[
					{
						label: 'Create Site',
					},
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

				<div class="space-y-12">
					<div v-if="$team.doc.onboarding.site_created">
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
								Select Bench Group
								<span class="text-sm text-gray-500"> (Optional) </span>
							</h2>
							<div class="mt-2 w-full space-y-2">
								<FormControl
									type="combobox"
									:options="
										options.private_groups.map((b) => ({
											label: b.title,
											value: b.name,
										}))
									"
									:modelValue="selectedGroup?.value"
									@update:modelValue="
										selectedGroup = options.private_groups.find(
											(option) => option.value === $event,
										)
									"
								/>
							</div>
						</div>
					</div>

					<div>
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

					<div>
						<h2 class="text-base font-medium leading-6 text-gray-900">
							Enter Subdomain
						</h2>
						<div class="mt-2 items-center">
							<div class="col-span-2 flex w-full">
								<input
									class="dark:[color-scheme:dark] z-10 h-7 w-full flex-1 rounded rounded-r-none border border-[--surface-gray-2] bg-surface-gray-2 py-1.5 pl-2 pr-2 text-base text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-modals hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
									placeholder="Subdomain"
									v-model="subdomain"
								/>
								<div
									class="flex items-center rounded-r bg-gray-100 px-4 text-base"
								>
									.{{ options.domain }}
								</div>
							</div>
						</div>

						<div class="mt-1">
							<ErrorMessage :message="$resources.subdomainExists.error" />
							<div
								v-if="$resources.subdomainExists.loading"
								class="text-sm text-gray-600"
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
							:disabled="
								!agreedToRegionConsent || !$resources.subdomainExists.data
							"
							@click="$resources.newSite.submit()"
							:loading="$resources.newSite.loading"
						>
							Create site and install {{ appDoc.title }}
						</Button>
					</div>
				</div>
				<div class="flex space-x-1">
					<div class="text-sm text-gray-600">
						Want to install <b>{{ appDoc.title }}</b> on an existing Site or
						Bench Group?
					</div>
					<a
						class="text-sm underline"
						href="https://docs.frappe.io/cloud/installing-an-app"
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
import { Breadcrumbs, debounce } from 'frappe-ui';
import Header from '../components/Header.vue';
import PlansCards from '../components/PlansCards.vue';
import { DashboardError } from '../utils/error';
import { validateSubdomain } from '../utils/site';

export default {
	name: 'InstallApp',
	props: {
		app: {
			type: String,
			required: true,
		},
	},
	pageMeta() {
		return {
			title: `Install ${this.appDoc.title} - Frappe Cloud`,
		};
	},
	components: {
		FBreadcrumbs: Breadcrumbs,
		PlansCards,
		Header,
	},
	data() {
		return {
			plan: '',
			subdomain: '',
			cluster: null,
			selectedPlan: null,
			selectedGroup: null,
			agreedToRegionConsent: false,
			sitePlan: null,
			trial: false,
		};
	},
	watch: {
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
		app() {
			return {
				url: 'press.api.marketplace.get',
				params: {
					app: this.app,
				},
				auto: true,
			};
		},
		installAppOptions() {
			return {
				url: 'press.api.marketplace.get_install_app_options',
				auto: true,
				params: {
					marketplace_app: this.app,
				},
				initialData: {
					domain: '',
					plans: [],
					clusters: [],
					private_groups: [],
				},
				onSuccess() {
					this.cluster =
						this.$resources.installAppOptions.data?.closest_cluster;
					if (this.$resources.installAppOptions.data?.plans.length > 0) {
						this.selectedPlan = this.$resources.installAppOptions.data.plans[0];
					}
				},
			};
		},
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				makeParams() {
					return {
						domain: this.$resources.installAppOptions.data?.domain,
						subdomain: this.subdomain,
					};
				},
				validate() {
					let error = validateSubdomain(this.subdomain);
					if (error) {
						throw new DashboardError(error);
					}
				},
				transform(data) {
					return !Boolean(data);
				},
			};
		},
		getTrialPlan() {
			return {
				url: 'press.api.site.get_trial_plan',
				auto: true,
			};
		},
		newSite() {
			if (!this.options) return;

			return {
				url: 'press.api.marketplace.create_site_for_app',
				makeParams() {
					this.sitePlan = this.selectedGroup
						? this.options.private_site_plan
						: this.options.public_site_plan;

					if (!this.$team.doc.onboarding.site_created) {
						this.sitePlan = this.trialPlan;
						this.trial = true;
					}
					return {
						subdomain: this.subdomain,
						site_plan: this.sitePlan,
						apps: [
							{
								app: 'frappe',
							},
							{
								app: this.app,
								plan: this.selectedPlan?.name,
							},
						],
						cluster: this.cluster,
						group: this.selectedGroup?.value,
						trial: this.trial,
					};
				},
				validate() {
					if (
						!this.$team.doc.payment_mode &&
						(this.$team.doc.onboarding.site_created ||
							!this.appDoc.show_for_new_site)
					) {
						throw new DashboardError('Please add a valid payment mode');
					}
					if (!this.selectedPlan && this.plans.length > 0) {
						throw new DashboardError('Please select a plan');
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
				onSuccess: (doc) => {
					if (doc.doctype === 'Site') {
						this.$router.push({
							name: 'Site Jobs',
							params: { name: doc.name },
						});
					} else if (doc.doctype === 'Site Group Deploy') {
						this.$router.push({
							name: 'CreateSiteForMarketplaceApp',
							params: { app: this.app },
							query: { siteGroupDeployName: doc.name },
						});
					}
				},
			};
		},
	},
	computed: {
		appDoc() {
			return this.$resources.app.data || {};
		},
		options() {
			return this.$resources.installAppOptions.data;
		},
		plans() {
			if (!this.$resources?.installAppOptions) return [];
			return this.options.plans.map((plan) => ({
				...plan,
				label:
					plan.price_inr === 0 || plan.price_usd === 0
						? 'Free'
						: `${this.$format.userCurrency(
								this.$team.doc.currency === 'INR'
									? plan.price_inr
									: plan.price_usd,
							)}/mo`,
				sublabel: ' ',
				features: plan.features.map((f) => ({
					value: f,
					icon: 'check-circle',
				})),
			}));
		},
		regions() {
			if (!this.selectedGroup) {
				return this.options.clusters;
			} else {
				return this.options.private_groups.find(
					(g) => g.name === this.selectedGroup.value,
				).clusters;
			}
		},
		trialPlan() {
			return this.$resources.getTrialPlan.data;
		},
	},
};
</script>
