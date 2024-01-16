<template>
	<div
		class="flex min-h-screen bg-gray-50"
		v-if="siteRequest.doc && saasProduct"
	>
		<ProductSignupPitch :saasProduct="saasProduct" class="w-[40%]" />
		<div class="w-full">
			<LoginBox
				:title="
					siteRequest.doc.status == 'Pending'
						? `Create your ${saasProduct.title} site`
						: ''
				"
			>
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
									: `You won't be charged during the 14-day trial period`
							}}
						</div>
					</div>
					<FormControl
						class="subdomain mt-2"
						label="Site Name"
						v-model="subdomain"
						@keydown.enter="siteRequest.createSite.submit()"
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
						@click="siteRequest.createSite.submit()"
						:loading="siteRequest.createSite.loading"
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
			</LoginBox>
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
							this.plan = this.selectedPlan;
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
					You won't be charged during the 14-day trial period. The plan you
					select here will become active after the trial period.
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
								this.plan = this.selectedPlan;
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
</template>
<script>
import { ErrorMessage, Progress } from 'frappe-ui';
import LoginBox from '@/views/partials/LoginBox.vue';
import { vElementSize } from '@vueuse/components';
import { validateSubdomain } from '@/utils';
import SitePlansCards from '../components/SitePlansCards.vue';
import ProductSignupPitch from '../components/ProductSignupPitch.vue';
import { plans } from '../data/plans';

export default {
	name: 'NewAppSite',
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
			progressErrorCount: 0
		};
	},
	resources: {
		siteRequest() {
			if (!this.$team?.doc?.onboarding.saas_site_request) return;
			return {
				type: 'document',
				doctype: 'SaaS Product Site Request',
				name: this.$team.doc.onboarding.saas_site_request,
				realtime: true,
				onSuccess(doc) {
					if (doc.status == 'Wait for Site') {
						this.siteRequest.getProgress.reload();
					}
				},
				whitelistedMethods: {
					createSite: {
						method: 'create_site',
						makeParams() {
							return { subdomain: this.subdomain, plan: this.plan };
						},
						validate() {
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
							} else if (this.progressErrorCount <= 10) {
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
		onResize({ width }) {
			this.inputPaddingRight = width + 10 + 'px';
		},
		goToDashboard() {
			window.location.reload();
		}
	},
	computed: {
		siteRequest() {
			return this.$resources.siteRequest;
		},
		saasProduct() {
			return this.$resources.siteRequest.doc.saas_product;
		},
		selectedPlanDescription() {
			if (!this.plan) return;
			if (!plans?.data) {
				return this.plan;
			}
			let plan = plans.data.find(plan => plan.name == this.plan);
			let country = this.$team.doc.country;
			let pricePerMonth = this.$format.userCurrency(
				country === 'India' ? plan.price_inr : plan.price_usd
			);
			return `${pricePerMonth} per month`;
		},
		progressError() {
			if (!this.siteRequest.getProgress.data?.error) return;
			if (this.progressErrorCount > 9) {
				return 'An error occurred. Please contact Frappe Cloud Support.';
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
