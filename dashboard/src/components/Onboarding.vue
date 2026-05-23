<template>
	<div class="mx-auto max-w-2xl rounded-lg border-0 px-2 sm:border sm:p-8">
		<div class="prose prose-sm max-w-none">
			<h1 class="text-2xl font-semibold">Bienvenue sur Frappe Cloud</h1>
			<p>
				Frappe Cloud facilite la gestion des sites et des applications comme ERPNext
				dans un tableau de bord facile à utiliser avec des fonctionnalités puissantes
				comme les sauvegardes automatiques, les domaines personnalisés, les certificats SSL,
				les applications personnalisées, les mises à jour automatiques et plus encore.
			</p>
		</div>
		<p class="mt-6 text-base text-ink-gray-8">
			Complétez les étapes ci-dessous pour débloquer les sites, les benches, les serveurs dédiés et
			plus encore.
		</p>
		<div class="mt-6 space-y-6">
			<div class="rounded-md">
				<div>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>1</TextInsideCircle>
							<span class="text-base font-medium"> Compte créé </span>
						</div>
						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<lucide-check class="h-3 w-3 text-white" />
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
							Une erreur est survenue lors de la création de votre site d'essai pour
							{{ pendingSiteRequest.title }}
						</span>
						<span class="text-base font-medium" v-else>
							Créer votre site d'essai {{ pendingSiteRequest.title }}
						</span>
					</div>
				</div>
				<div class="mt-2 pl-7" v-if="pendingSiteRequest.status == 'Error'">
					<p class="mt-2 text-p-base text-ink-gray-8">
						Veuillez contacter le support Frappe Cloud en cliquant sur le bouton ci-dessous.
					</p>
					<Button class="mt-2" link="/support"> Contacter le support </Button>
				</div>
				<div class="mt-2 pl-7" v-else>
					<p class="mt-2 text-p-base text-ink-gray-8">
						Vous pouvez essayer l'application {{ pendingSiteRequest.title }} gratuitement
						en cliquant sur le bouton ci-dessous.
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
						Continuer
					</Button>
				</div>
			</div>
			<div v-else-if="trialSite">
				<div class="flex items-center justify-between space-x-2">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>2</TextInsideCircle>
						<span class="text-base font-medium">
							Votre site d'essai est prêt
						</span>
					</div>
					<div
						class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
					>
						<lucide-check class="h-3 w-3 text-white" />
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
							<lucide-external-link class="ml-1 h-3.5 w-3.5 text-ink-gray-8" />
						</a>
					</div>
					<p class="mt-2 text-p-base text-ink-gray-8">
						Votre essai expire le
						<span class="font-medium">
							{{ $format.date(trialSite.trial_end_date, 'LL') }} </span
						>. Configurez la facturation maintenant pour garantir un accès ininterrompu à votre site.
					</p>
				</div>
			</div>
			<div v-else class="rounded-md">
				<div class="flex items-center space-x-2">
					<TextInsideCircle>2</TextInsideCircle>
					<div class="text-base font-medium">Créer votre premier site</div>
				</div>

				<Button
					class="ml-7 mt-4"
					:route="{ name: 'SignupAppSelector' }"
					variant="solid"
				>
					Créer
				</Button>
			</div>
			<!-- Step 3 - Complete Billing Setup -->
			<div
				class="rounded-md"
				:class="{
					'pointer-events-none opacity-50': !$team.doc.onboarding.site_created,
				}"
			>
				<div v-if="!isBillingSetupComplete">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>3</TextInsideCircle>
						<span class="text-base font-medium"> Compléter la configuration de facturation </span>
					</div>
					<div class="pl-7 mt-2" v-if="$team.doc.onboarding.site_created && trialSite">
						<p class="text-p-base text-ink-gray-8">
							Ajoutez vos informations de facturation et votre mode de paiement pour activer
							votre abonnement. Vous ne serez pas facturé avant la fin de votre essai le
							<span class="font-medium">
								{{ $format.date(trialSite.trial_end_date, 'LL') }}
							</span>
						</p>
						<Button class="mt-3" route="/billing"> Terminer la configuration </Button>
					</div>
				</div>
				<div v-else>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>3</TextInsideCircle>
							<span class="text-base font-medium">
								Configuration de facturation terminée
							</span>
						</div>
						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
					<div class="mt-1.5 pl-7 text-p-base text-ink-gray-8">
						<span v-if="$team.doc.payment_mode === 'Card'">
							La facturation automatique est activée
						</span>
						<span v-else-if="$team.doc.payment_mode === 'Prepaid Credits'">
							Solde du compte : {{ $format.userCurrency($team.doc.balance) }}
						</span>
					</div>
				</div>
			</div>

			<!-- Commented out - now using single step with redirect to billing page
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
							<lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
				</div>
			</div>
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
						<div
							class="flex w-full flex-row gap-2 rounded-md border p-1 text-p-base text-ink-gray-8"
						>
							<div
								class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
								:class="{
									'bg-surface-gray-2': isAutomatedBilling,
								}"
								@click="isAutomatedBilling = true"
							>
								Automated Billing
							</div>
							<div
								class="w-1/2 cursor-pointer rounded-sm py-1.5 text-center transition-all"
								:class="{
									'bg-surface-gray-2': !isAutomatedBilling,
								}"
								@click="isAutomatedBilling = false"
							>
								Add Money
							</div>
						</div>

						<div class="mt-2 w-full">
							<div v-if="isAutomatedBilling">
								<CardForm
									@success="onAddCardSuccess"
									:disableAddressForm="true"
								/>
							</div>
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
							<lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
					<div
						class="mt-1.5 pl-7 text-p-base text-ink-gray-8"
						v-if="$team.doc.payment_mode === 'Prepaid Credits'"
					>
						Account balance: {{ $format.userCurrency($team.doc.balance) }}
					</div>
				</div>
			</div>
			-->
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
			() => import('./CardWithDetails.vue'),
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
		isBillingSetupComplete() {
			return this.isBillingDetailsSet && Boolean(this.$team.doc.payment_mode);
		},
		minimumAmount() {
			return this.$team.doc.currency == 'DZD' ? 100 : 5;
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
