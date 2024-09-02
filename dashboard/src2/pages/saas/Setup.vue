<template>
	<div v-if="saasProduct">
		<div class="flex min-h-screen sm:bg-gray-50">
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
				<div class="relative h-full">
					<div class="relative z-10 mx-auto py-8 sm:w-max sm:py-32">
						<div class="flex flex-col items-center">
							<div class="mx-auto flex items-center space-x-2">
								<img
									class="inline-block h-7 w-7 rounded-sm"
									:src="saasProduct?.logo"
								/>
								<span
									class="select-none text-xl font-semibold tracking-tight text-gray-900"
								>
									{{ saasProduct?.title }}
								</span>
							</div>
						</div>
						<div
							class="mx-auto !w-full bg-white px-4 py-8 sm:mt-8 sm:min-w-[24rem] sm:rounded-lg sm:px-8 sm:shadow-xl"
						>
							<!-- Site Creation -->
							<div v-if="$resources.siteRequest && $resources.siteRequest?.doc">
								<!-- Site Creation Form (Site creation is yet not initiated) -->
								<div
									class="mb-6 text-center"
									v-if="$resources.siteRequest?.doc?.status == 'Pending'"
								>
									<span
										class="text-center text-lg font-medium leading-5 tracking-tight text-gray-900"
									>
										Fill in the details to create your site
									</span>
								</div>
								<form
									class="space-y-3"
									v-if="$resources.siteRequest?.doc?.status == 'Pending'"
									@submit.prevent="createSite()"
								>
									<FormControl
										label="Your Email"
										:modelValue="$team.doc.user"
										:disabled="true"
									/>
									<Form
										v-if="saasProductSignupFields.length > 0"
										:fields="saasProductSignupFields"
										v-model="signupValues"
									/>
									<ErrorMessage
										class="sm:max-w-[23rem]"
										:message="$resources.siteRequest?.createSite?.error"
									/>
									<Button
										class="w-full"
										variant="solid"
										:loading="
											findingClosestServer ||
											$resources.siteRequest?.createSite?.loading
										"
										loadingText="Creating Site"
									>
										Create Site
									</Button>
								</form>
								<!-- Site creation has been initiated but hasn't created till now -->
								<div
									v-else-if="
										$resources.siteRequest?.doc?.status == 'Wait for Site' ||
										$resources.siteRequest?.doc?.status ==
											'Completing Setup Wizard'
									"
								>
									<Progress
										label="Creating site"
										:value="
											$resources.siteRequest.getProgress.data?.progress || 0
										"
										size="md"
									/>
									<div class="mt-4 flex flex-row items-center gap-1">
										<Spinner class="w-3" />
										<p class="text-sm italic">
											{{
												$resources.siteRequest.getProgress.data?.current_step
													? $resources.siteRequest.getProgress.data
															?.current_step
													: !$resources.siteRequest.getProgress.data?.progress
													? 'Waiting for update'
													: 'Just a moment'
											}}
										</p>
									</div>
									<ErrorMessage
										class="mt-2 sm:max-w-[23rem]"
										:message="progressError"
									/>
									<div
										class="mt-2 text-p-base text-red-600"
										v-if="progressError"
									>
										There was an error creating your site. Please contact
										<a class="underline" href="/support">Frappe Cloud Support</a
										>.
									</div>
								</div>
								<!-- Site created -->
								<div
									v-else-if="
										$resources.siteRequest?.doc?.status == 'Site Created' &&
										siteRequest?.is_pending === true
									"
								>
									<div class="text-base text-gray-900">
										Your site
										<span class="font-semibold text-gray-900">{{
											$resources.siteRequest?.doc?.site
										}}</span>
										is ready.
									</div>
									<div
										class="py-3 text-base text-gray-900"
										v-if="$resources.siteRequest?.getLoginSid?.loading"
									>
										Logging in to your site...
									</div>
								</div>
							</div>
							<!-- Site request faced error -->
							<div v-if="siteRequest?.status == 'Error'">
								<div class="text-p-base text-red-600">
									There was an error creating your site. Please contact
									<a class="underline" href="/support">Frappe Cloud Support</a>.
								</div>
							</div>
							<!-- Site Details (Site creation done already) -->
							<div v-if="siteRequest?.is_pending === false">
								<div>
									<AlertBanner
										:showIcon="false"
										:type="
											isTrialEnded(siteRequest?.trial_end_date)
												? `error`
												: `warning`
										"
										class="col-span-1 mb-4 lg:col-span-2"
										:title="trialDays(siteRequest?.trial_end_date)"
										v-if="
											!isBillingDetailsSet ||
											!isPaymentModeSet ||
											siteRequest?.is_trial_plan
										"
									>
										<Button
											class="ml-auto"
											variant="outline"
											@click="subscribeNow"
										>
											Subscribe
										</Button>
									</AlertBanner>
									<!-- Site -->
									<div
										class="flex flex-col items-center justify-between gap-2.5 overflow-hidden whitespace-nowrap py-2.5 text-base"
									>
										<!-- Site name -->
										<p
											class="block font-medium text-gray-900 focus:outline-none"
											target="_blank"
										>
											{{ siteRequest?.site }}
										</p>
										<!-- Action Buttons -->
										<Button
											class="w-full"
											variant="outline"
											iconLeft="user"
											@click="() => loginAsTeam(siteRequest?.site)"
											:disabled="
												(loginAsTeamInProgressInSite &&
													loginAsTeamInProgressInSite !== siteRequest?.site) ||
												siteRequest?.site_status !== 'Active'
											"
											:loading="
												loginAsTeamInProgressInSite === siteRequest?.site
											"
											loadingText="Logging in ..."
										>
											Login to site</Button
										>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="absolute bottom-4 z-[1] flex w-full justify-center">
						<FrappeLogo class="h-4" />
					</div>
				</div>
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
			<!-- Subscribe Now Dialog -->
			<AppTrialSubscriptionDialog
				v-if="showAppTrialSubscriptionDialog"
				:site="siteRequest?.site"
				:currentPlan="siteRequest?.site_plan"
				:trialPlan="$resources.saasProduct?.doc?.trial_plan"
				v-model="showAppTrialSubscriptionDialog"
				@success="subscriptionConfirmed"
			/>
		</div>
	</div>
</template>
<script>
import { ErrorMessage, Progress, createResource, Badge } from 'frappe-ui';
import FCLogo from '@/components/icons/FCLogo.vue';
import FrappeLogo from '@/components/icons/FrappeLogo.vue';
import { vElementSize } from '@vueuse/components';
import SitePlansCards from '../../components/SitePlansCards.vue';
import { trialDays, isTrialEnded } from '../../utils/site';
import AlertBanner from '../../components/AlertBanner.vue';
import { toast } from 'vue-sonner';
import AppTrialSubscriptionDialog from '../../components/AppTrialSubscriptionDialog.vue';
import Form from '@/components/Form.vue';

export default {
	name: 'AppTrialSetup',
	props: ['productId'],
	directives: {
		'element-size': vElementSize
	},
	components: {
		FCLogo,
		FrappeLogo,
		SitePlansCards,
		AlertBanner,
		AppTrialSubscriptionDialog,
		Form
	},
	mounted() {
		// Open subscription dialog if hash is #subscription and billing details or payment mode is not set
		if (
			this.$route.hash === '#subscription' &&
			!(this.isBillingDetailsSet && this.isPaymentModeSet)
		) {
			this.$resources.getSiteRequest.promise.then(this.subscribeNow);
		}
	},
	data() {
		return {
			plan: null,
			showPlanDialog: false,
			selectedPlan: null,
			progressErrorCount: 0,
			findingClosestServer: false,
			closestCluster: null,
			loginAsTeamInProgressInSite: null,
			showAppTrialSubscriptionDialog: false,
			signupValues: {}
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
				doctype: 'Product Trial',
				name: this.productId,
				auto: true
			};
		},
		siteRequest() {
			if (!this.siteRequest && !this.siteRequest.is_pending) return;
			return {
				type: 'document',
				doctype: 'Product Trial Request',
				name: this.siteRequest.name,
				realtime: true,
				auto: true,
				onSuccess(doc) {
					if (
						doc.status == 'Wait for Site' ||
						doc.status == 'Completing Setup Wizard'
					) {
						this.$resources.siteRequest.getProgress.reload();
					}
				},
				whitelistedMethods: {
					createSite: {
						method: 'create_site',
						makeParams(params) {
							let cluster = params?.cluster;
							let signup_values = params?.signup_values;
							return {
								cluster,
								signup_values
							};
						},
						onSuccess() {
							this.$resources.siteRequest.getProgress.reload();
						},
						onerror(e) {
							console.log(e);
						}
					},
					getProgress: {
						method: 'get_progress',
						makeParams() {
							return {
								current_progress:
									this.$resources.siteRequest.getProgress.data?.progress || 0
							};
						},
						onSuccess(data) {
							this.progressErrorCount += 1;
							if (data.progress == 100) {
								this.$resources.siteRequest.getLoginSid.fetch();
							} else if (
								!(
									this.$resources.siteRequest.getProgress.error &&
									this.progressErrorCount <= 10
								)
							) {
								setTimeout(() => {
									this.$resources.siteRequest.getProgress.reload();
								}, 2000);
							}
						}
					},
					getLoginSid: {
						method: 'get_login_sid',
						onSuccess(data) {
							let sid = data;
							let loginURL = `https://${this.$resources.siteRequest.doc.site}/desk?sid=${sid}`;
							window.open(loginURL, '_self');
						}
					}
				}
			};
		}
	},
	methods: {
		async createSite() {
			let cluster = await this.getClosestCluster();
			return this.$resources.siteRequest.createSite.submit({
				cluster,
				signup_values: this.signupValues
			});
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
		loginAsTeam(site_name) {
			if (this.loginAsTeamInProgressInSite) return;
			this.loginAsTeamInProgressInSite = site_name;
			let todo = createResource({
				url: '/api/method/press.api.client.run_doc_method',
				params: {
					dt: 'Site',
					dn: site_name,
					method: 'login_as_team'
				},
				onSuccess: res => {
					this.loginAsTeamInProgressInSite = null;
					if (!res?.message) {
						toast.error("Couldn't login to the site");
						return;
					}
					window.open(res.message, '_blank');
				},
				onError: () => {
					toast.error("Couldn't login to the site");
				}
			});
			todo.fetch();
		},
		goToDashboard() {
			window.location.reload();
		},
		trialDays,
		isTrialEnded,
		subscribeNow() {
			this.showAppTrialSubscriptionDialog = true;
		},
		subscriptionConfirmed() {
			this.$resources.getSiteRequest.reload();
		}
	},
	computed: {
		siteRequest() {
			return this.$resources.getSiteRequest?.data ?? {};
		},
		saasProduct() {
			return this.$resources.saasProduct.doc;
		},
		saasProductSignupFields() {
			return this.saasProduct?.signup_fields ?? [];
		},
		progressError() {
			if (!this.$resources.siteRequest?.getProgress?.data?.error) return;
			if (this.progressErrorCount > 9) {
				return 'An error occurred. Please contact <a href="/support">Frappe Cloud Support</a>.';
			}
			if (this.progressErrorCount > 4) {
				return 'An error occurred';
			}
			return null;
		},
		isBillingDetailsSet() {
			return Boolean(this.$team.doc.billing_details?.name);
		},
		isPaymentModeSet() {
			return Boolean(this.$team.doc.payment_mode);
		}
	}
};
</script>
