<template>
	<div class="mx-auto max-w-2xl rounded-lg border-0 px-2 sm:border sm:p-8">
		<div class="prose prose-sm max-w-none">
			<h1 class="text-2xl font-semibold">Welcome to Frappe Cloud</h1>
			<p>
				Frappe Cloud makes it easy to manage sites and apps like ERPNext in an
				easy to use dashboard with powerful features like automatic backups,
				custom domains, SSL certificates, custom apps, automatic updates and
				more.
			</p>
		</div>
		<p class="mt-6 text-base text-gray-800">
			You are just few steps away from creating your first site.
		</p>
		<div class="mt-6 space-y-6">
			<div class="rounded-md">
				<div>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>1</TextInsideCircle>
							<span class="text-base font-medium"> Account created </span>
						</div>
						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<i-lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
				</div>
			</div>
			<!-- Step 2 - Create Site -->
			<div v-if="pendingSiteRequest">
				<div class="flex items-center justify-between space-x-2">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>2</TextInsideCircle>
						<span
							class="text-base font-medium"
							v-if="pendingSiteRequest.status == 'Error'"
						>
							There was an error creating your trial site for
							{{ pendingSiteRequest.title }}
						</span>
						<span class="text-base font-medium" v-else>
							Create your {{ pendingSiteRequest.title }} trial site
						</span>
					</div>
				</div>
				<div class="mt-2 pl-7" v-if="pendingSiteRequest.status == 'Error'">
					<p class="mt-2 text-p-base text-gray-800">
						Please contact Frappe Cloud support by clicking on the button below.
					</p>
					<Button class="mt-2" link="/support"> Contact Support </Button>
				</div>
				<div class="mt-2 pl-7" v-else>
					<p class="mt-2 text-p-base text-gray-800">
						You can try out the {{ pendingSiteRequest.title }} app for free by
						clicking on the button below.
					</p>
					<Button
						class="mt-2"
						:route="{
							name: 'SignupSetup',
							params: { productId: pendingSiteRequest.product_trial },
							query: {
								account_request: pendingSiteRequest.account_request,
							},
						}"
					>
						Continue
					</Button>
				</div>
			</div>
			<div v-else-if="trialSite">
				<div class="flex items-center justify-between space-x-2">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>2</TextInsideCircle>
						<span class="text-base font-medium">
							Your trial site is ready
						</span>
					</div>
					<div
						class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
					>
						<i-lucide-check class="h-3 w-3 text-white" />
					</div>
				</div>
				<div class="pl-7">
					<div class="mt-2">
						<a
							class="flex items-center text-base font-medium underline"
							:href="`https://${trialSite.host_name || trialSite.name}`"
							target="_blank"
						>
							https://{{ trialSite.host_name || trialSite.name }}
							<i-lucide-external-link class="ml-1 h-3.5 w-3.5 text-gray-800" />
						</a>
					</div>
					<p class="mt-2 text-p-base text-gray-800">
						Your trial is set to expire on
						<span class="font-medium">
							{{ $format.date(trialSite.trial_end_date, 'LL') }} </span
						>. Set up billing now to ensure uninterrupted access to your site.
					</p>
				</div>
			</div>
			<div v-else class="rounded-md">
				<div class="flex items-center space-x-2">
					<TextInsideCircle>2</TextInsideCircle>
					<div class="text-base font-medium">Create your first site</div>
				</div>

				<Button class="ml-7 mt-4" :route="{ name: 'SignupAppSelector' }">
					Create
				</Button>
			</div>
			<!-- Step 3 - Update Billing Details -->
			<div
				class="rounded-md"
				:class="{
					'pointer-events-none opacity-50': !$team.doc.onboarding.site_created,
				}"
			>
				<div v-if="!isBillingDetailsSet">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>3</TextInsideCircle>
						<span class="text-base font-medium"> Update billing details </span>
					</div>
					<div class="pl-7" v-if="$team.doc.onboarding.site_created">
						<UpdateBillingDetailsForm @updated="onBillingAddresUpdateSuccess" />
					</div>
				</div>
				<div v-else>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>3</TextInsideCircle>
							<span class="text-base font-medium">
								Billing address updated
							</span>
						</div>
						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<i-lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
				</div>
			</div>
			<!-- Step 4 - Add Payment Method -->
			<div
				class="rounded-md"
				:class="{ 'pointer-events-none opacity-50': !isBillingDetailsSet }"
			>
				<div v-if="!$team.doc.payment_mode">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>4</TextInsideCircle>
						<span class="text-base font-medium"> Add a payment mode </span>
					</div>

					<div class="mt-4 pl-7" v-if="isBillingDetailsSet">
						<!-- Payment Method Selector -->
						<div
							class="flex w-full flex-row gap-2 rounded-md border p-1 text-p-base text-gray-800"
						>
							<div
								class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
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

						<div class="mt-2 w-full">
							<!-- Automated Billing Section -->
							<div v-if="isAutomatedBilling">
								<!-- Stripe Card -->
								<CardForm
									@success="onAddCardSuccess"
									:disableAddressForm="true"
								/>
							</div>
							<!-- Purchase Prepaid Credit -->
							<div v-else class="mt-3">
								<BuyPrepaidCreditsForm
									:isOnboarding="true"
									:minimumAmount="minimumAmount"
									@success="onBuyCreditsSuccess"
								/>
							</div>
						</div>
					</div>
				</div>
				<!-- Payment Method Added -->
				<div v-else>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>4</TextInsideCircle>
							<span
								class="text-base font-medium"
								v-if="$team.doc.payment_mode === 'Card'"
							>
								Automatic billing setup completed
							</span>
							<span
								class="text-base font-medium"
								v-if="$team.doc.payment_mode === 'Prepaid Credits'"
							>
								Wallet balance updated
							</span>
						</div>
						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<i-lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
					<div
						class="mt-1.5 pl-7 text-p-base text-gray-800"
						v-if="$team.doc.payment_mode === 'Prepaid Credits'"
					>
						Account balance: {{ $format.userCurrency($team.doc.balance) }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import TextInsideCircle from './TextInsideCircle.vue';

export default {
	name: 'Onboarding',
	emits: ['payment-mode-added'],
	components: {
		UpdateBillingDetailsForm: defineAsyncComponent(
			() => import('./UpdateBillingDetailsForm.vue'),
		),
		CardWithDetails: defineAsyncComponent(
			() => import('../../src/components/CardWithDetails.vue'),
		),
		BuyPrepaidCreditsForm: defineAsyncComponent(
			() => import('./BuyPrepaidCreditsForm.vue'),
		),
		OnboardingAppSelector: defineAsyncComponent(
			() => import('./OnboardingAppSelector.vue'),
		),
		AlertBanner: defineAsyncComponent(() => import('./AlertBanner.vue')),
		TextInsideCircle,
		CardForm: defineAsyncComponent(
			() => import('../components/billing/CardForm.vue'),
		),
	},
	data() {
		return {
			billingInformation: {
				cardHolderName: '',
				country: '',
				gstin: '',
			},
			isAutomatedBilling: true,
		};
	},
	methods: {
		onBuyCreditsSuccess() {
			this.$team.reload();
			this.$emit('payment-mode-added');
		},
		onAddCardSuccess() {
			this.$team.reload();
			this.$emit('payment-mode-added');
		},
		onBillingAddresUpdateSuccess() {
			this.$team.reload();
		},
	},
	computed: {
		isBillingDetailsSet() {
			return Boolean(this.$team.doc.billing_details?.name);
		},
		minimumAmount() {
			return this.$team.doc.currency == 'INR' ? 100 : 5;
		},
		pendingSiteRequest() {
			return this.$team.doc.pending_site_request;
		},
		trialSite() {
			return this.$team.doc.trial_sites?.[0];
		},
	},
	resources: {
		availableApps() {
			return {
				url: 'press.api.marketplace.get_marketplace_apps_for_onboarding',
				auto: true,
			};
		},
	},
};
</script>
