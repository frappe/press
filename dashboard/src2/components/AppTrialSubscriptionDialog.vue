<template>
	<Dialog
		:options="{
			title: 'Subscribe Now',
			size: '2xl'
		}"
		v-model="showDialog"
	>
		<template v-slot:body-content>
			<div class="border-0">
				<p class="text-base text-gray-800">
					You are just few steps away from creating your first site.
				</p>
				<div class="mt-6 space-y-6">
					<!-- Step 1 : Choose a plan -->
					<div>
						<div v-if="step == 1">
							<div class="flex items-center space-x-2">
								<TextInsideCircle>1</TextInsideCircle>
								<span class="text-base font-medium"> Choose Site Plan </span>
							</div>
							<div class="pl-7">
								<SitePlansCards
									:hideRestrictedPlans="true"
									v-model="selectedPlan"
									class="mt-4"
								/>
								<p></p>
								<div class="flex w-full justify-end">
									<Button
										class="mt-2 w-full sm:w-fit"
										variant="solid"
										@click="confirmPlan"
									>
										Confirm Plan
									</Button>
								</div>
							</div>
						</div>
						<div v-else>
							<div class="flex items-center justify-between space-x-2">
								<div class="flex items-center space-x-2">
									<TextInsideCircle>1</TextInsideCircle>
									<span class="text-base font-medium">
										Site plan selected ({{ selectedPlan.name }})
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
					<!-- Step 2 : Update Billing Details -->
					<div
						class="rounded-md"
						:class="{ 'pointer-events-none opacity-50': step < 2 }"
					>
						<div v-if="step <= 2">
							<div class="flex items-center space-x-2">
								<TextInsideCircle>2</TextInsideCircle>
								<span class="text-base font-medium">
									Update billing details
								</span>
							</div>
							<div class="pl-7" v-if="step == 2">
								<UpdateBillingDetailsForm
									@updated="onBillingAddresUpdateSuccess"
								/>
							</div>
						</div>
						<div v-else>
							<div class="flex items-center justify-between space-x-2">
								<div class="flex items-center space-x-2">
									<TextInsideCircle>2</TextInsideCircle>
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
					<!-- Step 3 : Add Payment Method -->
					<div
						class="rounded-md"
						:class="{ 'pointer-events-none opacity-50': step < 3 }"
					>
						<div v-if="step <= 3">
							<div class="flex items-center space-x-2">
								<TextInsideCircle>3</TextInsideCircle>
								<span class="text-base font-medium"> Add a payment mode </span>
							</div>

							<div class="mt-4 pl-7" v-if="step == 3">
								<!-- Payment Method Selector -->
								<div
									class="flex w-full flex-row gap-2 rounded-md border p-1 text-p-base text-gray-800"
								>
									<div
										class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
										:class="{
											'bg-gray-100': isAutomatedBilling
										}"
										@click="isAutomatedBilling = true"
									>
										Automated Billing
									</div>
									<div
										class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
										:class="{
											'bg-gray-100': !isAutomatedBilling
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
										<StripeCard2
											@complete="onAddCardSuccess"
											:withoutAddress="true"
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
									<TextInsideCircle>3</TextInsideCircle>
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
					<!-- Step 4 : Finalize -->
					<div>
						<div
							v-if="step < 4"
							class="pointer-events-none rounded-md opacity-50"
						>
							<div class="flex items-center justify-between space-x-2">
								<div class="flex items-center space-x-2">
									<TextInsideCircle>4</TextInsideCircle>
									<div class="text-base font-medium">
										Subscription confirmation
									</div>
								</div>
							</div>
						</div>
						<div v-else-if="isChangingPlan">
							<div class="flex items-center justify-between space-x-2">
								<div class="flex items-center space-x-2">
									<TextInsideCircle>4</TextInsideCircle>
									<div class="text-base font-medium">Updating Site Plan</div>
								</div>
							</div>
							<div class="mt-3 pl-7">
								<Button :loading="true" loadingText="Updating Site Plan...">
									Site Plan Updated
								</Button>
							</div>
						</div>
						<div v-else>
							<div class="flex items-center justify-between space-x-2">
								<div class="flex items-center space-x-2">
									<TextInsideCircle>4</TextInsideCircle>
									<span class="text-base font-medium">
										🎉 Subscription Confirmed
									</span>
								</div>
								<div
									class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
								>
									<i-lucide-check class="h-3 w-3 text-white" />
								</div>
							</div>
							<div class="mt-1.5 pl-7">
								<div class="flex items-center space-x-2">
									<span class="text-p-base text-gray-800">
										Your subscription has been confirmed.<br />
										If any of your site has been disabled, it will be enabled
										soon.
									</span>
								</div>
								<div class="flex w-full justify-end">
									<Button
										class="mt-2 w-full sm:w-fit"
										variant="solid"
										iconRight="arrow-right"
										@click="showDialog = false"
									>
										Back to Dashboard
									</Button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { createResource } from 'frappe-ui';
import { defineAsyncComponent } from 'vue';
import TextInsideCircle from './TextInsideCircle.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'AppTrialSubscriptionDialog',
	components: {
		SitePlansCards: defineAsyncComponent(() => import('./SitePlansCards.vue')),
		StripeCard2: defineAsyncComponent(() =>
			import('../components/StripeCard.vue')
		),
		UpdateBillingDetailsForm: defineAsyncComponent(() =>
			import('./UpdateBillingDetailsForm.vue')
		),
		CardWithDetails: defineAsyncComponent(() =>
			import('../../src/components/CardWithDetails.vue')
		),
		BuyPrepaidCreditsForm: defineAsyncComponent(() =>
			import('./BuyPrepaidCreditsForm.vue')
		),
		AlertBanner: defineAsyncComponent(() => import('./AlertBanner.vue')),
		TextInsideCircle
	},
	props: ['site', 'currentPlan', 'trialPlan'],
	data() {
		return {
			step: 1,
			selectedPlan: null,
			billingInformation: {
				cardHolderName: '',
				country: '',
				gstin: ''
			},
			isAutomatedBilling: true,
			isChangingPlan: false
		};
	},
	emits: ['update:modelValue', 'success'],
	mounted() {
		if (this.trialPlan && this.currentPlan !== this.trialPlan) {
			this.selectedPlan = {
				name: this.trialPlan
			};
		} else {
			this.selectedPlan = null;
		}
	},
	methods: {
		confirmPlan() {
			if (!this.selectedPlan) {
				toast.error('Please select a plan');
				return;
			}
			this.step = 2;
		},
		onBillingAddresUpdateSuccess() {
			this.$team.reload();
			if (this.$team.doc.payment_mode) {
				this.step = 4;
				this.changePlan();
			} else {
				this.step = 3;
			}
		},
		onBuyCreditsSuccess() {
			this.$team.reload();
			this.step = 4;
			this.changePlan();
		},
		onAddCardSuccess() {
			this.$team.reload();
			this.step = 4;
			this.changePlan();
		},
		changePlan() {
			if (this.isChangingPlan) return;
			this.isChangingPlan = true;
			const plan_name = this.selectedPlan?.name;
			let request = createResource({
				url: '/api/method/press.api.client.run_doc_method',
				params: {
					dt: 'Site',
					dn: this.site,
					method: 'set_plan',
					args: {
						plan: plan_name
					}
				},
				onSuccess: res => {
					this.isChangingPlan = false;
					this.$team.reload();
					this.$emit('success');
				},
				onError: () => {
					this.isChangingPlan = false;
					toast.error('Failed to change the plan. Please try again later.');
					this.showDialog = false;
				}
			});
			request.submit();
		}
	},
	computed: {
		isBillingDetailsSet() {
			return Boolean(this.$team.doc.billing_details?.name);
		},
		minimumAmount() {
			return this.$team.doc.currency == 'INR' ? 100 : 5;
		},
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
