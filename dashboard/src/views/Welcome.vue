<template>
	<div class="p-8">
		<h1 class="text-xl font-semibold">
			Welcome to Frappe Cloud
		</h1>
		<p class="text-base">
			To start using Frappe Cloud, complete the following steps to get your
			account up and running.
		</p>
		<SectionCard class="mt-6">
			<div class="-mt-2"></div>
			<div class="divide-y">
				<button
					class="flex items-start w-full px-6 py-4 cursor-pointer focus:outline-none focus:shadow-outline"
					:class="{
						'bg-green-50 text-green-700': isStepCompleted(step),
						'bg-gray-50 text-gray-700': isStepSkipped(step),
						'hover:bg-blue-50': isNextStep(step),
						'cursor-not-allowed pointer-events-none':
							(!isStepCompleted(step) && !isNextStep(step)) ||
							isStepSkipped(step)
					}"
					v-for="step in steps"
					:key="step.step_name"
					:disabled="
						isStepCompleted(step) || !isNextStep(step) || step.disabled
					"
					@click="isNextStep(step) ? step.click() : null"
				>
					<FeatherIcon
						:name="stepIcon(step)"
						:stroke-width="isStepCompleted(step) ? 3 : 2"
						class="flex-shrink-0 w-4 h-4 mt-0.5"
					/>
					<div class="ml-4 text-left">
						<div class="text-base font-medium">
							<span>
								{{ step.step_name }}
							</span>
						</div>
						<div
							class="mt-1 text-sm"
							:class="
								isStepCompleted(step)
									? 'text-green-800 opacity-75'
									: 'text-gray-800'
							"
						>
							{{ step.description }}
						</div>
						<div
							class="mt-3"
							v-if="
								step.skippable && !isStepSkipped(step) && !isStepCompleted(step)
							"
						>
							<Button
								@click.stop="
									$resources.skipOnboardingStep.fetch({
										step_name: step.step_name
									})
								"
								:loading="$resources.skipOnboardingStep.loading"
							>
								Skip
							</Button>
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
		<TransferCreditsDialog
			v-if="showTransferCreditsDialog"
			:show.sync="showTransferCreditsDialog"
			@success="refreshOnboarding"
			:minimum-amount="$account.team.currency == 'INR' ? 1000 : 10"
		/>
	</div>
</template>

<script>
export default {
	name: 'Welcome',
	components: {
		StripeCard: () => import('@/components/StripeCard'),
		TransferCreditsDialog: () => import('@/components/TransferCreditsDialog')
	},
	resources: {
		skipOnboardingStep() {
			return {
				method: 'press.api.account.skip_onboarding_step',
				onSuccess() {
					this.refreshOnboarding();
				}
			};
		}
	},
	watch: {
		onboardingComplete: {
			handler(value) {
				if (value) {
					this.$router.replace('/sites');
				}
			},
			immediate: true
		}
	},
	computed: {
		onboardingComplete() {
			return this.steps.every(d => ['Completed', 'Skipped'].includes(d.status));
		}
	},
	data() {
		return {
			showAddCardDialog: false,
			showTransferCreditsDialog: false,
			countryList: [],
			steps: this.getSteps()
		};
	},
	methods: {
		getSteps() {
			let onboardingSteps = this.$account.team?.onboarding;
			return onboardingSteps
				.filter(d => d.status !== 'Not Applicable')
				.map(d => {
					let icon = {
						'Create Team': '',
						'Add Billing Information': 'credit-card',
						'Transfer Credits': 'dollar-sign',
						'Create Site': 'plus-circle'
					}[d.step_name];

					let description = {
						'Create Team': `Your team ${this.$account.team?.name} has been created.`,
						'Add Billing Information':
							"After adding your billing information you will get a free $25 credit. Sites you create will use your free credits first.",
						'Transfer Credits':
							'As an ERPNext Partner, you have the privilege to use your ERPNext.com credits for creating Frappe Cloud sites.',
						'Create Site':
							'Creating a new site is as easy as choosing a subdomain and a plan.'
					}[d.step_name];

					let click = {
						'Add Billing Information': () => (this.showAddCardDialog = true),
						'Transfer Credits': () => (this.showTransferCreditsDialog = true),
						'Create Site': () => this.$router.push('/sites/new')
					}[d.step_name];

					return {
						...d,
						icon,
						description,
						click,
						skippable:
							d.step_name === 'Add Billing Information' &&
							this.$account.team.erpnext_partner
					};
				});
		},
		isNextStep(step) {
			let stepIndex = this.steps.indexOf(step);
			let prevStep = this.steps[stepIndex - 1];
			if (
				prevStep &&
				['Completed', 'Skipped'].includes(prevStep.status) &&
				step.status == 'Pending'
			) {
				return true;
			}
			return false;
		},
		isStepCompleted(step) {
			return step.status === 'Completed';
		},
		isStepSkipped(step) {
			return step.status === 'Skipped';
		},
		async skipStep(step) {
			await this.$call('press.api.account.skip_onboarding_step', {
				step: step.step_name
			});
			this.refreshOnboarding();
		},
		stepIcon(step) {
			return {
				Completed: 'check',
				Skipped: 'minus',
				Pending: step.icon
			}[step.status];
		},
		afterCardAdd() {
			this.showAddCardDialog = false;
			this.refreshOnboarding();
		},
		async refreshOnboarding() {
			await this.$account.fetchAccount();
			this.steps = this.getSteps();
		}
	}
};
</script>
