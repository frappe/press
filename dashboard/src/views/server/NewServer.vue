<template>
	<WizardCard v-if="options">
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new server</h1>
		</div>
		<Steps :steps="steps">
			<template
				v-slot="{ active: activeStep, next, previous, hasPrevious, hasNext }"
			>
				<div class="mt-8"></div>
				<Hostname
					:options="options"
					v-show="activeStep.name === 'Hostname'"
					v-model:title="title"
					v-model:selectedRegion="selectedRegion"
				/>
				<AppServerPlans
					v-model:selectedAppPlan="selectedAppPlan"
					:options="options"
					v-show="activeStep.name === 'AppServerPlan'"
				/>
				<DBServerPlans
					v-model:selectedDBPlan="selectedDBPlan"
					:options="options"
					v-show="activeStep.name === 'DBServerPlan'"
				/>
				<ErrorMessage :error="validationMessage" />
				<div class="mt-4">
					<!-- Region consent checkbox -->
					<div class="my-6" v-if="!hasNext">
						<input
							id="region-consent"
							type="checkbox"
							class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
							v-model="agreedToRegionConsent"
						/>
						<label
							for="region-consent"
							class="ml-1 text-sm font-semibold text-gray-900"
						>
							I agree that the laws of the region selected by me shall stand
							applicable to me and Frappe.
						</label>
					</div>


					<div class="flex justify-between">
						<Button
							@click="previous"
							:class="{
								'pointer-events-none opacity-0': !hasPrevious
							}"
						>
							Back
						</Button>
						<Button
							appearance="primary"
							@click="nextStep(activeStep, next)"
							:class="{
								'pointer-events-none opacity-0': !hasNext
							}"
						>
							Next
						</Button>
						<Button
							v-show="!hasNext"
							appearance="primary"
							@click="$resources.newServer.submit()"
							:loading="$resources.newServer.loading"
						>
							Create Servers
						</Button>
					</div>
				</div>
			</template>
		</Steps>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
import Steps from '@/components/Steps.vue';
import Hostname from './NewServerHostname.vue';
import AppServerPlans from './NewAppServerPlans.vue';
import DBServerPlans from './NewDBServerPlans.vue';
export default {
	name: 'NewServer',
	components: {
		WizardCard,
		Steps,
		Hostname,
		AppServerPlans,
		DBServerPlans,
	},
	data() {
		return {
			title: null,
			options: null,
			selectedRegion: null,
			steps: [
				{
					name: 'Hostname',
					validate: () => {
						return this.title && this.selectedRegion;
					}
				},
				{
					name: 'AppServerPlan',
					validate: () => {
						return this.selectedAppPlan;
					}
				},
				{
					name: 'DBServerPlan',
					validate: () => {
						return this.selectedDBPlan;
					}
				},
			],
			agreedToRegionConsent: false
		};
	},
	async mounted() {
		this.options = await this.$call('press.api.server.options');
		this.options.app_plans = this.options.app_plans.map(plan => {
			plan.disabled = !this.$account.hasBillingInfo;
			return plan;
		});
		this.options.db_plans = this.options.db_plans.map(plan => {
			plan.disabled = !this.$account.hasBillingInfo;
			return plan;
		});
	},
	computed: {},
	methods: {
		async nextStep(activeStep, next) {
			next();
		}
	}
};
</script>
