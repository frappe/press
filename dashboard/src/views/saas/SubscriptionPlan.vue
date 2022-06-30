<template>
	<div>
		<Alert
			v-if="activePlan && activePlan.is_free"
			title="Trial"
			class="mb-4"
			type="alert"
		>
			Your trial ends {{ trialEndsText() }} after which your site will get
			suspended. Select a plan below to avoid suspension.
		</Alert>
		<div class="mb-4" v-if="activePlan">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-xl font-semibold">Change Plan</h1>
					<p class="text-sm mt-1">{{ app }} plans available for {{ site }}</p>
				</div>
				<Button
					:disabled="selectedPlan.is_free"
					class="relative top-0 right-0 mb-4"
					type="primary"
					@click="toggleCheckoutDialog()"
					>{{
						selectedPlan === activePlan ? 'Renew Plan' : 'Change Plan'
					}}</Button
				>
			</div>
		</div>

		<div
			v-if="plansData"
			class="mx-auto grid flex-1 grid-cols-1 gap-6 md:grid-cols-3"
		>
			<AppPlanCard
				v-for="plan in plansData"
				:plan="plan"
				:key="plan.name"
				:selected="selectedPlan == plan"
				@click.native="handleCardClick(plan)"
			/>
		</div>

		<Dialog class="z-100" title="Checkout Details" v-model="showCheckoutDialog">
			<div
				v-if="step == 'Confirm Checkout'"
				class="grid grid-cols-1 gap-2 md:grid-cols-2"
			>
				<Input
					type="select"
					:options="paymentOptions"
					label="Payment Option"
					v-model="selectedOption"
				/>
				<Input
					v-if="selectedPlan"
					type="text"
					label="Selected Plan"
					v-model="selectedPlan.plan_title"
					readonly
				/>
			</div>

			<div v-if="selectedPlan" class="mb-4">
				<p class="text-base font-bold ml-3 mb-4">{{ getTotalAmount() }}</p>
				<Input type="text" label="Total price" v-model="totalAmount" readonly />
			</div>
			<div v-if="step == 'Confirm Checkout'">
				<Input
					class="mb-4"
					v-if="$account.team.payment_mode === 'Partner Credits'"
					type="checkbox"
					label="Use Partner Credits"
					v-model="usePartnerCredits"
				/>
			</div>

			<div v-if="step == 'Add Card Details'" class="text-sm">Card Details</div>
			<div
				v-if="step == 'Add Card Details'"
				class="form-input my-2 block w-full py-2 pl-3"
				ref="card-element"
			></div>

			<div class="mt-2 flex w-full justify-between">
				<StripeLogo />
				<div v-if="step == 'Add Card Details'">
					<Button
						@click="
							() => {
								showCheckoutDialog = false;
								step = 'Confirm Checkout';
								selectedOption = 'Monthly';
							}
						"
					>
						Cancel
					</Button>
					<Button
						class="ml-2"
						type="primary"
						@click="onBuyClick"
						:loading="paymentInProgress"
					>
						Pay
					</Button>
				</div>
				<div v-if="step == 'Confirm Checkout'">
					<Button
						type="primary"
						@click="$resources.changePlan.submit()"
						:loading="$resources.changePlan.loading"
					>
						Next
					</Button>
				</div>
			</div>

			<div v-if="step == 'Setting up Stripe'" class="mt-8 flex justify-center">
				<Spinner class="h-4 w-4 text-gray-600" />
			</div>
		</Dialog>
	</div>
</template>

<script>
import AppPlanCard from './AppPlanCard.vue';
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';
import { utils } from '@/utils';

export default {
	name: 'SubscriptionPlan',
	props: { subName: String, subData: Object },
	components: {
		AppPlanCard,
		StripeLogo
	},
	data() {
		return {
			app: '',
			site: '',
			plansData: null,
			selectedPlan: null,
			activePlan: null,
			trial_end_date: null,
			showCheckoutDialog: false,
			usePartnerCredits: false,
			step: 'Confirm Checkout',
			clientSecret: null,
			paymentOptions: ['Monthly', 'Yearly'],
			selectedOption: 'Monthly',
			totalAmount: ''
		};
	},
	methods: {
		handleCardClick(plan) {
			this.selectedPlan = plan;
			this.$emit('change', plan);
		},
		switchToNewPlan() {
			this.$resources.changePlan.submit();
		},
		toggleCheckoutDialog() {
			this.showCheckoutDialog = true;
		},
		trialEndsText() {
			return utils.methods.trialEndsInDaysText(
				this.subData.site.trial_end_date
			);
		},
		getTotalAmount() {
			let multiple = this.selectedOption === 'Yearly' ? 12 : 1;
			if (this.$account.team.country === 'India') {
				this.totalAmount = 'INR ' + this.selectedPlan.price_inr * multiple;
			} else {
				this.totalAmount = 'USD ' + this.selectedPlan.price_usd * multiple;
			}
		},
		async onBuyClick() {
			this.paymentInProgress = true;
			let payload = await this.stripe.confirmCardPayment(this.clientSecret, {
				payment_method: {
					card: this.card
				}
			});

			this.paymentInProgress = false;
			if (payload.error) {
				this.errorMessage = payload.error.message;
			} else {
				this.errorMessage = null;
				this.showCheckoutDialog = false;
				this.step = 'Confirm Checkout';
				this.$notify({
					title: 'Payment request received!',
					message:
						'Your plan will be change as soon as we get the payment confirmation',
					icon: 'check',
					color: 'green'
				});
			}
		}
	},
	resources: {
		plans() {
			return {
				method: 'press.api.saas.get_plans_info',
				params: {
					name: this.subName
				},
				auto: true,
				onSuccess(result) {
					this.plansData = result.plans;
					this.trial_end_date = result.trial_end_date;
					this.selectedPlan = result.plans.filter(plan => {
						if (plan.is_selected) {
							return plan;
						}
					})[0];
					this.activePlan = this.selectedPlan;
					this.site = result.site;
					this.app = result.app_name;
				}
			};
		},
		changePlan() {
			return {
				method: 'press.api.saas.change_plan',
				params: {
					name: this.subName,
					new_plan: this.selectedPlan,
					option: this.selectedOption,
					partner_credits: this.usePartnerCredits
				},
				async onSuccess(data) {
					if (data.payment_type === 'postpaid') {
						let { payment_type, publishable_key, client_secret } = data;
						this.showCheckoutDialog = true;
						this.step = 'Setting up Stripe';
						this.clientSecret = client_secret;
						this.stripe = await loadStripe(publishable_key);
						this.elements = this.stripe.elements();

						let theme = this.$theme;
						let style = {
							base: {
								color: theme.colors.black,
								fontFamily: theme.fontFamily.sans.join(', '),
								fontSmoothing: 'antialiased',
								fontSize: '13px',
								'::placeholder': {
									color: theme.colors.gray['400']
								}
							},
							invalid: {
								color: theme.colors.red['600'],
								iconColor: theme.colors.red['600']
							}
						};
						this.card = this.elements.create('card', {
							hidePostalCode: true,
							style: style,
							classes: {
								complete: '',
								focus: 'bg-gray-100'
							}
						});

						this.step = 'Add Card Details';
						this.$nextTick(() => {
							this.card.mount(this.$refs['card-element']);
						});

						this.card.addEventListener('change', event => {
							this.cardErrorMessage = event.error?.message || null;
						});
						this.card.addEventListener('ready', () => {
							this.ready = true;
						});
					} else {
						this.$resources.plans.reload();
						this.$notify({
							title: 'Plan Changed Successfully!',
							icon: 'check',
							color: 'green'
						});
					}
				},
				onError(e) {
					this.$notify({
						title: e,
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	}
};
</script>
