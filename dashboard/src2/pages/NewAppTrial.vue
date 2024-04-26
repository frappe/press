<template>
	<div v-if="saasProduct">
		<div class="flex min-h-screen sm:bg-gray-50">
			<ProductSignupPitch
				class="order-1 hidden sm:block"
				v-if="saasProduct"
				:saasProduct="saasProduct"
			/>
			<div
				class="flex w-full items-start justify-center pt-32"
				v-if="$resources.getSiteRequest.error"
			>
				<div class="rounded-md bg-white p-5 sm:shadow-xl">
					<div class="text-lg text-red-600">
						{{ $resources.getSiteRequest.error.messages[0] }}
					</div>
				</div>
			</div>
			<div class="relative w-full" v-if="saasProduct">
				<LoginBox
					:title="
						siteRequest?.doc?.status == 'Pending'
							? `Create your ${saasProduct.title} site`
							: ''
					"
				>
					<div v-if="completedSites">
						<div>
							<div class="text-base text-gray-900">
								{{
									completedSites.length > 1
										? 'You have already created the following sites:'
										: 'You have already created the following site:'
								}}
							</div>
							<ul class="mt-2">
								<li
									v-for="site in completedSites"
									:key="site"
									class="whitespace-nowrap rounded p-2.5 text-base focus-within:ring focus-within:ring-gray-200 hover:bg-gray-100"
								>
									<a
										:href="`https://${site.site}`"
										class="block font-medium text-gray-900 underline focus:outline-none"
										target="_blank"
									>
										{{ site.site }}
									</a>
									<div class="mt-1.5 text-base text-gray-600">
										{{ trialDays(site.trial_end_date) }}
									</div>
								</li>
							</ul>
						</div>
						<!-- {{ completedSites }} -->
					</div>
					<div v-if="siteRequest?.doc">
						<div class="space-y-3" v-if="siteRequest.doc.status == 'Pending'">
							<FormControl
								label="Your Email"
								:modelValue="$team.doc.user"
								:disabled="true"
							/>
							<div class="cursor-pointer" @click.stop="showPlanDialog = true">
								<label class="text-xs text-gray-600">Choose a plan</label>
								<Button class="w-full">
									<span class="text-base text-gray-900" v-if="plan">
										{{ selectedPlanDescription }}
									</span>
									<span class="text-base text-gray-600" v-else>
										No plan selected
									</span>
								</Button>
								<div class="mt-1 text-xs text-gray-600">
									{{
										plan === 'Trial'
											? ''
											: `You won't be charged during the ${saasProduct.trial_days}-day trial period`
									}}
								</div>
							</div>
							<FormControl
								class="subdomain mt-2"
								label="Site Name"
								v-model="subdomain"
								@keydown.enter="createSite"
							>
								<template #suffix>
									<div
										ref="domainSuffix"
										v-element-size="onResize"
										class="flex select-none items-center text-base text-gray-600"
									>
										.{{ saasProduct.domain || 'frappe.cloud' }}
									</div>
								</template>
							</FormControl>
							<ErrorMessage :message="siteRequest.createSite.error" />
							<Button
								class="w-full"
								variant="solid"
								@click="createSite"
								:loading="
									findingClosestServer || siteRequest.createSite.loading
								"
							>
								Create
							</Button>
						</div>
						<div v-else-if="siteRequest.doc.status == 'Wait for Site'">
							<Progress
								label="Creating site"
								:value="siteRequest.getProgress.data?.progress || 0"
								size="md"
							/>
							<ErrorMessage class="mt-2" :message="progressError" />
							<Button
								class="mt-2"
								v-if="siteRequest.getProgress.error && progressErrorCount > 9"
								route="/"
							>
								&#8592; Back to Dashboard
							</Button>
						</div>
						<div v-else-if="siteRequest.doc.status == 'Site Created'">
							<div class="text-base text-gray-900">
								Your site
								<span class="font-semibold text-gray-900">{{
									siteRequest.doc.site
								}}</span>
								is ready.
							</div>
							<div class="py-3 text-base text-gray-900">
								{{
									siteRequest.getLoginSid.loading
										? 'Logging in to your site...'
										: ''
								}}
							</div>
						</div>
						<div v-else-if="siteRequest.doc.status == 'Error'">
							<div class="text-p-base text-red-600">
								There was an error creating your site. Please contact
								<a class="underline" href="/support">Frappe Cloud Support</a>.
							</div>
						</div>
					</div>
				</LoginBox>
				<div class="absolute bottom-12 left-1/2 -translate-x-1/2">
					<Dropdown
						:options="[
							{ label: 'Log out', onClick: () => $session.logout.submit() }
						]"
					>
						<Button variant="ghost">
							<span class="text-gray-600">
								{{ $team.doc.user }}
							</span>
						</Button>
					</Dropdown>
				</div>
			</div>
			<Dialog
				:options="{
					title: 'Choose Plan',
					size: '4xl',
					actions: [
						{
							label: 'Select plan',
							variant: 'solid',
							onClick: () => {
								this.plan = this.selectedPlan.name;
								this.showPlanDialog = false;
							}
						},
						{
							label: 'Cancel',
							onClick: () => {
								this.plan = null;
								this.showPlanDialog = false;
							}
						}
					]
				}"
				v-model="showPlanDialog"
			>
				<template #body-content>
					<p class="text-p-base text-gray-900">
						You won't be charged during the {{ saasProduct.trial_days }}-day
						trial period. The plan you select here will become active after the
						trial period.
					</p>
					<SitePlansCards v-model="selectedPlan" class="mt-4" />
				</template>
				<template #actions>
					<div class="flex items-center">
						<Button
							class="order-1 ml-2"
							variant="solid"
							@click="
								() => {
									this.plan = this.selectedPlan.name;
									this.showPlanDialog = false;
								}
							"
						>
							Select Plan
						</Button>
						<Button
							class="ml-auto"
							@click="
								() => {
									this.plan = null;
									this.selectedPlan = null;
									this.showPlanDialog = false;
								}
							"
						>
							Cancel
						</Button>
					</div>
				</template>
			</Dialog>
		</div>
	</div>
</template>
<script>
import { ErrorMessage, Progress } from 'frappe-ui';
import LoginBox from '@/views/partials/LoginBox.vue';
import { vElementSize } from '@vueuse/components';
import { validateSubdomain } from '@/utils';
import SitePlansCards from '../components/SitePlansCards.vue';
import ProductSignupPitch from '../components/ProductSignupPitch.vue';
import { getPlans } from '../data/plans';
import { trialDays } from '../utils/site';

export default {
	name: 'NewAppTrial',
	props: ['productId'],
	directives: {
		'element-size': vElementSize
	},
	components: {
		LoginBox,
		SitePlansCards,
		ProductSignupPitch
	},
	data() {
		return {
			subdomain: null,
			plan: null,
			inputPaddingRight: null,
			showPlanDialog: false,
			selectedPlan: null,
			progressErrorCount: 0,
			findingClosestServer: false,
			closestCluster: null
		};
	},
	resources: {
		getSiteRequest() {
			return {
				url: 'press.api.account.get_site_request',
				params: { product: this.productId },
				auto: true
			};
		},
		saasProduct() {
			return {
				type: 'document',
				doctype: 'SaaS Product',
				name: this.productId
			};
		},
		siteRequest() {
			if (!this.pendingSiteRequest || this.completedSites.length) return;
			return {
				type: 'document',
				doctype: 'SaaS Product Site Request',
				name: this.pendingSiteRequest,
				realtime: true,
				onSuccess(doc) {
					if (doc.status == 'Wait for Site') {
						this.siteRequest.getProgress.reload();
					}
				},
				whitelistedMethods: {
					createSite: {
						method: 'create_site',
						makeParams(params) {
							let cluster = params?.cluster;
							return { subdomain: this.subdomain, plan: this.plan, cluster };
						},
						validate() {
							if (!this.plan) {
								return 'Please select a plan';
							}
							return validateSubdomain(this.subdomain);
						},
						onSuccess() {
							this.siteRequest.getProgress.reload();
						}
					},
					getProgress: {
						method: 'get_progress',
						makeParams() {
							return {
								current_progress:
									this.siteRequest.getProgress.data?.progress || 0
							};
						},
						onSuccess(data) {
							this.progressErrorCount += 1;
							if (data.progress == 100) {
								this.siteRequest.getLoginSid.fetch();
							} else if (
								!(
									this.siteRequest.getProgress.error &&
									this.progressErrorCount <= 10
								)
							) {
								setTimeout(() => {
									this.siteRequest.getProgress.reload();
								}, 2000);
							}
						}
					},
					getLoginSid: {
						method: 'get_login_sid',
						onSuccess(data) {
							let sid = data;
							let loginURL = `https://${this.siteRequest.doc.site}/desk?sid=${sid}`;
							window.location.href = loginURL;
						}
					}
				}
			};
		}
	},
	methods: {
		async createSite() {
			let cluster = await this.getClosestCluster();
			return this.siteRequest.createSite.submit({ cluster });
		},
		async getClosestCluster() {
			if (this.closestCluster) return this.closestCluster;
			let proxyServers = Object.keys(this.saasProduct.proxy_servers);
			if (proxyServers.length > 0) {
				this.findingClosestServer = true;
				let promises = proxyServers.map(server => this.getPingTime(server));
				let results = await Promise.allSettled(promises);
				let fastestServer = results.reduce((a, b) =>
					a.value.pingTime < b.value.pingTime ? a : b
				);
				let closestServer = fastestServer.value.server;
				let closestCluster = this.saasProduct.proxy_servers[closestServer];
				if (!this.closestCluster) {
					this.closestCluster = closestCluster;
				}
				this.findingClosestServer = false;
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
		onResize({ width }) {
			this.inputPaddingRight = width + 10 + 'px';
		},
		goToDashboard() {
			window.location.reload();
		},
		trialDays
	},
	computed: {
		pendingSiteRequest() {
			return this.$resources.getSiteRequest.data?.pending || null;
		},
		completedSites() {
			return this.$resources.getSiteRequest.data?.completed || [];
		},
		siteRequest() {
			return this.$resources.siteRequest;
		},
		saasProduct() {
			return this.$resources.saasProduct.doc;
		},
		selectedPlanDescription() {
			if (!this.plan) return;
			let plan = getPlans().find(plan => plan.name == this.plan);
			let country = this.$team.doc.country;
			let pricePerMonth = this.$format.userCurrency(
				country === 'India' ? plan.price_inr : plan.price_usd,
				0
			);
			return `${pricePerMonth} per month`;
		},
		progressError() {
			if (!this.siteRequest?.getProgress.data?.error) return;
			if (this.progressErrorCount > 9) {
				return 'An error occurred. Please contact <a href="/support">Frappe Cloud Support</a>.';
			}
			if (this.progressErrorCount > 4) {
				return 'An error occurred';
			}
			return null;
		}
	}
};
</script>
<style scoped>
.subdomain :deep(input) {
	padding-right: v-bind(inputPaddingRight);
}
</style>
