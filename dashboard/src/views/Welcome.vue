<template>
	<div class="p-8">
		<h1 class="text-xl font-semibold">
			Welcome to Frappe Cloud
		</h1>
		<p>
			To start using Frappe Cloud, complete the following steps to get your
			account up and running.
		</p>
		<SectionCard class="mt-6">
			<div class="-mt-2"></div>
			<div class="divide-y">
				<button
					class="flex items-start w-full px-6 py-4 cursor-pointer focus:outline-none focus:shadow-outline"
					:class="{
						'bg-green-50 text-green-700': step.done,
						'hover:bg-blue-50': step.nextStep,
						'cursor-not-allowed': !step.done && !step.nextStep
					}"
					v-for="step in steps"
					:key="step.name"
					:disabled="step.done || !step.nextStep || step.disabled"
					@click="step.nextStep ? step.click() : null"
				>
					<FeatherIcon
						:name="step.done ? 'check' : step.icon"
						:stroke-width="step.done ? 4 : 2"
						class="flex-shrink-0 w-4 h-4 my-1"
					/>
					<div class="ml-4 text-left">
						<div class="font-medium">
							{{ step.name }}
						</div>
						<div
							class="mt-1 text-sm"
							:class="step.done ? 'text-green-800 opacity-75' : 'text-gray-800'"
						>
							{{ step.description }}
						</div>
					</div>
				</button>
			</div>
			<div class="-mb-2"></div>
		</SectionCard>
		<div class="mt-4" v-if="onboardingComplete">
			Onboarding Complete! Redirecting to sites...
		</div>
		<Dialog title="Add Billing Information" v-model="showAddCardDialog">
			<StripeCard
				v-if="showAddCardDialog"
				class="mb-1"
				@complete="afterCardAdd"
			/>
		</Dialog>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
import Dialog from '@/components/Dialog';

export default {
	name: 'Welcome',
	components: {
		StripeCard,
		Dialog
	},
	resources: {
		onboarding: {
			method: 'press.api.account.onboarding',
			auto: true,
			onSuccess(onboarding) {
				let foundNextStep = false;
				this.steps = this.steps.map(step => {
					step.done = onboarding[step.name];
					if (!foundNextStep && !step.done) {
						step.nextStep = true;
						foundNextStep = true;
					} else {
						step.nextStep = false;
					}
					return step;
				});

				this.onboardingComplete = onboarding.complete;
				if (this.onboardingComplete) {
					setTimeout(() => {
						this.$router.replace('/sites');
					}, 2000);
				}
			}
		}
	},
	data() {
		let team = this.$store.account.team?.name || '';
		return {
			showAddCardDialog: false,
			onboardingComplete: false,
			steps: [
				{
					name: 'Create a Team',
					done: true,
					icon: '',
					description: `Your team ${team} has been created`
				},
				{
					name: 'Add Billing Information',
					description:
						"After adding your billing information you will get a free $25 credit. Sites you create will use your free credits first. If you don't like the experience you can cancel your subscription anytime.",
					done: false,
					icon: 'credit-card',
					click: () => {
						this.showAddCardDialog = true;
					},
					disabled: false
				},
				{
					name: 'Create your first site',
					done: false,
					icon: 'plus-circle',
					description:
						'Creating a new site is as easy as choosing a subdomain and a plan',
					click: () => {
						this.$router.push('/sites/new');
					}
				}
			]
		};
	},
	methods: {
		afterCardAdd() {
			this.showAddCardDialog = false;
			this.reloadUntilAddCardIsTrue();
		},
		async reloadUntilAddCardIsTrue() {
			let cardStep = this.steps[1];
			if (!cardStep.done) {
				cardStep.disabled = true;
				await this.$resources.onboarding.reload();
				setTimeout(() => {
					this.reloadUntilAddCardIsTrue();
				}, 1000);
			} else {
				cardStep.disabled = false;
			}
		}
	}
};
</script>
