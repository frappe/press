<template>
	<Dialog
		:options="{
			title: showSetupSubscription ? 'Setup Subscription' : 'Change Plan',
			size: step === 'site-plans' ? '3xl' : '3xl',
		}"
		v-model="show"
	>
		<template #body-content>
		<!-- steps are for users without payment method added,
		 otherwise user will only go through just the initial step to change plan  -->

			<div v-if="step === 'site-plans'">
				<!-- doing this weird thing because progress with intervals doesn't rerender on moving to new step for some reason -->
				<!-- TODO: fix it in frappe-ui -->
				<Progress
					v-if="showSetupSubscription"
					class="mt-8 mb-4"
					size="md"
					:label="progressLabel"
					:interval-count="3"
					:intervals="true"
					:value="32"
				/>
				<SitePlansCards
					v-model="plan"
					:isPrivateBenchSite="!$site.doc.group_public"
					:isDedicatedServerSite="$site.doc.is_dedicated_server"
					:selectedProvider="$site.doc.server_provider"
				/>
				<div class="mt-4 text-xs text-gray-700">
					<ProductSupportBanner />
				</div>
				<ErrorMessage class="mt-2" :message="$site.setPlan.error" />
			</div>

			<div v-else-if="step === 'billing-details'">
				<Progress
					class="my-8"
					size="md"
					:label="progressLabel"
					:interval-count="3"
					:intervals="true"
					:value="65"
				/>
				<div class="mb-5 inline-flex gap-1.5 text-base text-gray-700">
					<FeatherIcon class="h-4" name="info" />
					<span> Add billing details to your account before proceeding.</span>
				</div>
				<BillingDetails ref="billingRef" @back="step= 'site-plans'" @success="step = 'add-payment-mode'" />
			</div>

			<div v-else-if="step === 'add-payment-mode'">
				<Progress
					class="my-8"
					:label="progressLabel"
					size="md"
					:interval-count="3"
					:intervals="true"
					:value="99"
				/>
				<div
					class="mb-5 flex w-full flex-row gap-2 rounded-md border p-1 text-p-base text-gray-800"
				>
					<div
						class="w-1/2 cursor-pointer rounded-[7px] py-1.5 text-center transition-all"
						:class="{
							'bg-gray-100': isAutomatedBilling,
						}"
						@click="isAutomatedBilling = true"
					>
						Add Card
					</div>
					<div
						class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
						:class="{
							'bg-gray-100': !isAutomatedBilling,
						}"
						@click="isAutomatedBilling = false"
					>
						Add Prepaid Credits
					</div>
				</div>

				<div>
					<div
						v-if="isAutomatedBilling"
						class="mb-5 flex items-center gap-2 text-sm text-gray-700"
					>
						<FeatherIcon class="h-4" name="info" />
						<span>
							Adding a card will enable automated billing for your account. You
							will be charged automatically at the end of your billing cycle.
						</span>
					</div>
					<div
						v-else
						class="mb-5 flex items-center gap-2 text-sm text-gray-700"
					>
						<FeatherIcon class="h-4" name="info" />
						<span>
							Adding prepaid credits will allow you to manually recharge your
							account balance. You can use this balance to pay for your plan.
						</span>
					</div>
				</div>

				<CardForm
					v-if="isAutomatedBilling"
					@success="paymentModeAdded"
					:showAddressForm="false"
				/>
				<PrepaidCreditsForm
					v-else
					:minimumAmount="
						$team.doc?.currency === 'INR' ? plan.price_inr : plan.price_usd
					"
					:type="'Purchase Plan'"
					:docName="plan.name"
					@success="paymentModeAdded"
				/>
			</div>
		</template>
		<template #actions v-if="step === 'site-plans'">
			<div class="mb-2 text-center text-xs text-gray-600">
				Change plans later anytime. Billing is prorated.
			</div>
			<Button
				variant="solid"
				:disabled="!plan || ($site?.doc && plan === $site.doc.plan)"
				@click="handleNext()"
				class="w-full"
			>
				{{
					!$team.doc.payment_mode ||
					!$team.doc.billing_details ||
					!Object.keys(this.$team.doc.billing_details).length
						? (plan ? `Select Plan: ${planDisplayTitle(plan)}` : 'Next')
						: $site.doc?.current_plan?.is_trial_plan
							? 'Upgrade Plan'
							: 'Change plan'
				}}
			</Button>
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource, Progress } from 'frappe-ui';
import SitePlansCards from './SitePlansCards.vue';
import { getPlans, getPlan } from '../data/plans';
import CardForm from './billing/CardForm.vue';
import BillingDetails from './billing/BillingDetails.vue';
import PrepaidCreditsForm from './billing/PrepaidCreditsForm.vue';
import ProductSupportBanner from './ProductSupportBanner.vue';

export default {
	name: 'ManageSitePlansDialog',
	components: {
		CardForm,
		Progress,
		SitePlansCards,
		BillingDetails,
		PrepaidCreditsForm,
	},
	props: {
		site: {
			type: String,
			required: true,
		},
	},
	data() {
		return {
			show: true,
			plan: null,
			step: 'site-plans',
			isAutomatedBilling: true,
			showAddPaymentModeDialog: false,
			showBillingDetailsDialog: false,
		};
	},
	watch: {
		site: {
			immediate: true,
			handler(siteName) {
				if (siteName) {
					if (this.$site?.doc?.plan) {
						this.plan = getPlan(this.$site.doc.plan);
					}
				}
			},
		},
	},
	methods: {
		handleNext() {
			if (
				!this.$team.doc.billing_details ||
				!Object.keys(this.$team.doc.billing_details).length
			) {
				this.step = 'billing-details';
				this.$team.reload();
			} else if (!this.$team.doc.payment_mode) {
				this.step = 'add-payment-mode';
			} else {
				this.changePlan();
			}
		},
		changePlan() {
			return this.$site.setPlan.submit(
				{ plan: this.plan.name },
				{
					onSuccess: () => {
						this.show = false;
						let plan = getPlans().find(
							(plan) => plan.name === this.$site.doc.plan,
						);
						let formattedPlan = plan
							? `${this.$format.planTitle(plan)}/mo`
							: this.$site.doc.plan;
						this.$toast.success(`Plan changed to ${formattedPlan}`);
					},
				},
			);
		},
		planDisplayTitle(plan) {
			const display = this.$format.planDisplay(plan, false);
			return `${display.title}${display.unit}`;
		},
		paymentModeAdded() {
			this.$team.reload();
			this.show = false;
			this.$toast.success(
				'Payment mode added and the plan has been changed successfully',
			);
			this.changePlan();
		},
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		showSetupSubscription() {
			return (
				!this.$team.doc.payment_mode ||
				!this.$team.doc.billing_details ||
				!Object.keys(this.$team.doc.billing_details).length
			);
		},
		progressLabel() {
			if (this.step === 'site-plans') {
				return 'Select a plan';
			} else if (this.step === 'billing-details') {
				return 'Add billing details';
			} else if (this.step === 'add-payment-mode') {
				return 'Add payment mode';
			}
		},
	},
};
</script>
