<template>
	<div class="space-y-6">
		<!-- Step 1 : Choose a plan -->
		<div v-if="step <= 1">
			<div class="flex items-center space-x-2">
				<TextInsideCircle>1</TextInsideCircle>
				<span class="text-base font-medium"> Choose Site Plan </span>
			</div>
			<div class="pl-7" v-if="step == 1">
				<SitePlansCards
					v-if="teamCurrency"
					:teamCurrency="teamCurrency"
					v-model="selectedPlan"
					class="mt-4"
				/>
				<p></p>
				<div class="flex w-full justify-end">
					<Button
						class="mt-2 w-full sm:w-fit"
						variant="solid"
						@click="confirmSitePlan"
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
		<!-- Step 2 : Choose address -->
		<div
			v-if="step <= 2"
			:class="{ 'pointer-events-none opacity-50': step < 2 }"
		>
			<div class="flex items-center space-x-2">
				<TextInsideCircle>2</TextInsideCircle>
				<span class="text-base font-medium"> Provide Billing Details </span>
			</div>
			<div class="pl-7" v-if="step == 2">
				<UpdateAddressForm @updated="onSuccessAddressUpdate" />
			</div>
		</div>
		<div v-else>
			<div class="flex items-center justify-between space-x-2">
				<div class="flex items-center space-x-2">
					<TextInsideCircle>2</TextInsideCircle>
					<span class="text-base font-medium"> Address Confirmed </span>
				</div>
				<div
					class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
				>
					<i-lucide-check class="h-3 w-3 text-white" />
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
							<!-- Offer -->
							<p class="my-3 text-p-sm text-gray-800">
								🎉 You are eligible for
								<span class="font-medium">{{ free_credits }}</span> worth of
								free credits for enabling automated billing.
							</p>
							<!-- Stripe Card -->
							<StripeCard2 @complete="onAddCardSuccess" />
						</div>
						<!-- Purchase Prepaid Credit -->
						<div v-else class="mt-3">
							<b>Not Implemented</b>
							<!-- <BuyPrepaidCreditsForm
											:isOnboarding="true"
											:minimumAmount="minimumAmount"
											@success="onBuyCreditsSuccess"
										/> -->
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
							v-if="team?.data?.payment_mode === 'Card'"
						>
							Automatic billing setup completed
						</span>
						<span
							class="text-base font-medium"
							v-if="team?.data?.payment_mode === 'Prepaid Credits'"
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
					v-if="team?.data?.payment_mode === 'Prepaid Credits'"
				>
					Account balance:
					{{ $format.currency(team?.data?.balance, team?.data?.currency, 0) }}
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import { toast } from 'vue-sonner';

export default {
	name: 'In Desk Billing Onboarding',
	inject: ['team'],
	components: {
		TextInsideCircle: defineAsyncComponent(() =>
			import('../../../components/TextInsideCircle.vue')
		),
		SitePlansCards: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/SitePlanCards.vue')
		),
		UpdateAddressForm: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/UpdateAddressForm.vue')
		),
		StripeCard2: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/StripeCard.vue')
		)
	},
	data() {
		return {
			selectedPlan: {
				name: ''
			},
			step: 1,
			isAutomatedBilling: true
		};
	},
	computed: {
		teamCurrency() {
			return this.team?.data?.currency || 'INR';
		},
		free_credits() {
			return this.$format.currency(
				this.teamCurrency == 'INR'
					? window.free_credits_inr
					: window.free_credits_usd,
				this.teamCurrency,
				0
			);
		}
	},
	methods: {
		confirmSitePlan() {
			if (!this.selectedPlan || !this.selectedPlan.name) {
				toast.error('Please select a plan');
				return;
			}
			this.step = 2;
		},
		onSuccessAddressUpdate() {
			this.step = 3;
			this.team.reload();
		},
		onAddCardSuccess() {
			this.step = 4;
			this.team.reload();
		}
	}
};
</script>
