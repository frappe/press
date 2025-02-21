<template>
	<Dialog
		:options="{
			title: 'Change Plan',
			size: step === 'site-plans' ? '5xl' : 'lg',
		}"
		v-model="show"
	>
		<template #body-content>
			<!-- steps are for users without payment method added, 
		 otherwise user will only go through just the initial step to change plan  -->

			<div v-if="step == 'site-plans'">
				<SitePlansCards
					v-model="plan"
					:isPrivateBenchSite="!$site.doc.group_public"
					:isDedicatedServerSite="$site.doc.is_dedicated_server"
				/>
				<div class="mt-4 text-xs text-gray-700">
					<div
						class="flex items-center rounded bg-gray-50 p-2 text-p-base font-medium text-gray-800"
					>
						<i-lucide-badge-check class="h-4 w-8 text-gray-600" />
						<span>
							<strong>Support</strong> covers only issues of Frappe apps and not
							functional queries. You can raise a support ticket for Frappe
							Cloud issues for all plans.
						</span>
					</div>
				</div>
				<ErrorMessage class="mt-2" :message="$site.setPlan.error" />
			</div>

			<div v-else-if="step == 'billing-details'">
				<div class="mb-5 inline-flex gap-1.5 text-base text-gray-700">
					<FeatherIcon class="h-4" name="info" />
					<span> Add billing details to your account before proceeding.</span>
				</div>
				<BillingDetails ref="billingRef" @success="step = 'add-payment-mode'" />
			</div>

			<div v-else-if="step == 'add-payment-mode'">
				<div class="mb-5 inline-flex gap-1.5 text-base text-gray-700">
					<FeatherIcon class="h-4" name="info" />
					<span> Add a payment mode before upgrading your plan. </span>
				</div>
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
						Automated Billing
					</div>
					<div
						class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
						:class="{
							'bg-gray-100': !isAutomatedBilling,
						}"
						@click="isAutomatedBilling = false"
					>
						Add Money
					</div>
				</div>
				<CardForm v-if="isAutomatedBilling" @success="paymentModeAdded" />
				<PrepaidCreditsForm
					v-else
					:minimumAmount="
						$team.doc?.currency === 'INR' ? plan.price_inr : plan.price_usd
					"
					@success="paymentModeAdded"
				/>
			</div>
		</template>
		<template #actions v-if="step === 'site-plans'">
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
						? 'Next'
						: $site.doc?.current_plan?.is_trial_plan
							? 'Upgrade Plan'
							: 'Change plan'
				}}
			</Button>
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import SitePlansCards from './SitePlansCards.vue';
import { getPlans, getPlan } from '../data/plans';
import CardForm from './billing/CardForm.vue';
import BillingDetails from './billing/BillingDetails.vue';
import PrepaidCreditsForm from './billing/PrepaidCreditsForm.vue';

export default {
	name: 'ManageSitePlansDialog',
	components: {
		CardForm,
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
			showMessage: false,
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
	},
};
</script>
